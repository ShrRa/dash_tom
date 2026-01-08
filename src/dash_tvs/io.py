from __future__ import annotations

import pandas as pd

from .schema import (
    COL_BAND,
    COL_FLUX,
    COL_FLUX_ERR,
    COL_ID,
    COL_SOURCE,
    COL_TIME,
    OPTIONAL_COL_OBJECT,
    validate_canonical_df,
)


def add_mock_diaSourceId(
    df: pd.DataFrame,
    *,
    object_col: str = "objectId",
    time_col: str = "expMidptMJD",
    source_name: str = "LSST",
) -> pd.DataFrame:
    """
    Add mock diaSourceId and source columns.

    diaSourceId format:
        int("1" + object_index(2 digits) + observation_index(4 digits))

    object_index is based on sorted unique object IDs in the input df.
    observation_index is based on time sorting within each object.
    """
    df = df.copy()

    if object_col not in df.columns:
        raise ValueError(f"Cannot create mock diaSourceId: missing {object_col}")

    if time_col not in df.columns:
        raise ValueError(f"Cannot create mock diaSourceId: missing {time_col}")

    object_ids = sorted(df[object_col].unique())

    dia_ids = []
    for obj_idx, obj_id in enumerate(object_ids, start=1):
        df_obj = df[df[object_col] == obj_id].sort_values(time_col)
        for obs_idx, row_idx in enumerate(df_obj.index, start=1):
            dia_id_str = f"1{obj_idx:02d}{obs_idx:04d}"
            dia_ids.append((row_idx, int(dia_id_str)))

    df[COL_ID] = pd.Series({idx: dia_id for idx, dia_id in dia_ids}, name=COL_ID)
    df[COL_SOURCE] = source_name
    return df


def from_lsst_pickle_df(
    df: pd.DataFrame,
    *,
    time_col: str = "expMidptMJD",
    band_col: str = "band",
    flux_col: str = "psfFlux",
    flux_err_col: str = "psfFluxErr",
    object_col: str = "objectId",
    source_name: str = "LSST",
    generate_mock_id_if_missing: bool = True,
) -> pd.DataFrame:
    """
    Convert your LSST-ish dataframe into canonical schema.

    Output columns:
      - diaSourceId
      - mjd
      - band
      - flux
      - flux_err (if available)
      - source
      - objectId (if available)
    """
    df_in = df.copy()

    # Ensure ID + source exist
    if COL_ID not in df_in.columns:
        if not generate_mock_id_if_missing:
            raise ValueError(f"Missing {COL_ID} and generate_mock_id_if_missing=False")
        df_in = add_mock_diaSourceId(
            df_in, object_col=object_col, time_col=time_col, source_name=source_name
        )
    else:
        if COL_SOURCE not in df_in.columns:
            df_in[COL_SOURCE] = source_name

    # Build canonical frame
    out = pd.DataFrame(
        {
            COL_ID: df_in[COL_ID],
            COL_TIME: df_in[time_col],
            COL_BAND: df_in[band_col].astype(str),
            COL_FLUX: df_in[flux_col].astype(float),
            COL_SOURCE: df_in[COL_SOURCE].astype(str),
        }
    )

    if flux_err_col in df_in.columns:
        out[COL_FLUX_ERR] = df_in[flux_err_col].astype(float)

    if object_col in df_in.columns:
        out[OPTIONAL_COL_OBJECT] = df_in[object_col]

    # Normalize band values (strip whitespace etc.)
    out[COL_BAND] = out[COL_BAND].str.strip()

    # Validate
    validate_canonical_df(out, allow_empty=True)

    return out
