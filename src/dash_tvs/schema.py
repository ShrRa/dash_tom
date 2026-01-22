from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd


BANDS = ("u", "g", "r", "i", "z", "y")

# Canonical column names
COL_ID = "diaSourceId" # unique identifier for each observation. No assumptions about ordering
COL_TIME = "mjd"
COL_BAND = "band"
COL_SOURCE = "source" # e.g. "LSST"; for uploading data from other surveys
COL_FLUX = "flux"
COL_FLUX_ERR = "flux_err"
COL_ACTIVE = "active" # boolean flag for visibility for future plotting
COL_OFFSET = "offset"
COL_FLUX_PLOT = "flux_plot"

OPTIONAL_COL_OBJECT = "objectId"


@dataclass(frozen=True)
class CanonicalSchema:
    required: tuple[str, ...] = (
        COL_ID,
        COL_TIME,
        COL_BAND,
        COL_SOURCE,
        COL_FLUX,
    )
    optional: tuple[str, ...] = (
        COL_FLUX_ERR,
        OPTIONAL_COL_OBJECT,
    )


SCHEMA = CanonicalSchema()


class SchemaError(ValueError):
    pass


def validate_canonical_df(
    df: pd.DataFrame,
    *,
    allow_empty: bool = False,
    allowed_bands: Optional[Iterable[str]] = BANDS,
) -> None:
    """
    Validate that df contains the canonical columns and basic sanity constraints.
    Raises SchemaError if invalid.
    """
    missing = [c for c in SCHEMA.required if c not in df.columns]
    if missing:
        raise SchemaError(f"Missing required columns: {missing}")

    if not allow_empty and len(df) == 0:
        raise SchemaError("DataFrame is empty.")

    # Basic dtype/NA sanity
    if df[COL_ID].isna().any():
        raise SchemaError(f"{COL_ID} contains NA values.")
    if df[COL_TIME].isna().any():
        raise SchemaError(f"{COL_TIME} contains NA values.")
    if df[COL_BAND].isna().any():
        raise SchemaError(f"{COL_BAND} contains NA values.")
    if df[COL_SOURCE].isna().any():
        raise SchemaError(f"{COL_SOURCE} contains NA values.")
    if df[COL_FLUX].isna().any():
        raise SchemaError(f"{COL_FLUX} contains NA values.")

    if allowed_bands is not None:
        allowed = set(allowed_bands)
        bad = sorted(set(df[COL_BAND].unique()) - allowed)
        if bad:
            raise SchemaError(f"Unexpected band values: {bad}. Allowed: {sorted(allowed)}")

    # Uniqueness is strongly recommended (not strictly required if you later support duplicates)
    if df[COL_ID].duplicated().any():
        # Don't hard-fail; raise a loud warning-like error for now.
        # If you want to allow duplicates later, change this to a warning.
        raise SchemaError(f"{COL_ID} contains duplicate values (must be unique for editing/selection).")
