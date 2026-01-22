from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd

from .schema import (
    BANDS,
    COL_ACTIVE,
    COL_BAND,
    COL_FLUX,
    COL_FLUX_PLOT,
    COL_ID,
    COL_OFFSET,
    COL_SOURCE,
    COL_TIME,
    COL_FLUX_ERR,
    OPTIONAL_COL_OBJECT,
    validate_canonical_df,
)


OffsetKey = Tuple[str, str]  # (source, band)


@dataclass
class LCSession:
    """
    Holds raw data (immutable by convention) and edit state (small deltas).
    Produces derived df_view on demand.

    Edits stored:
      - inactive_ids: set of diaSourceId
      - offsets: dict[(source, band)] -> float
      - visibility: bands + sources
      - df_added: additional points (canonical schema)
    """
    df_raw: pd.DataFrame

    inactive_ids: set[int] = field(default_factory=set)
    offsets: Dict[OffsetKey, float] = field(default_factory=dict)

    vis_bands: Dict[str, bool] = field(default_factory=lambda: {b: True for b in BANDS})
    vis_sources: Dict[str, bool] = field(default_factory=dict)  # filled from data on init

    df_added: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())

    def __post_init__(self) -> None:
        validate_canonical_df(self.df_raw, allow_empty=True)

        # init source visibility from df_raw
        if not self.vis_sources:
            sources = sorted(self.df_raw[COL_SOURCE].unique()) if len(self.df_raw) else []
            self.vis_sources = {s: True for s in sources}

        # Ensure df_added is canonical if not empty
        if len(self.df_added):
            validate_canonical_df(self.df_added, allow_empty=True)

    def set_band_visible(self, band: str, visible: bool) -> None:
        self.vis_bands[str(band)] = bool(visible)

    def set_source_visible(self, source: str, visible: bool) -> None:
        self.vis_sources[str(source)] = bool(visible)

    def set_offset(self, source: str, band: str, value: float) -> None:
        self.offsets[(str(source), str(band))] = float(value)

    def toggle_active(self, ids: Iterable[int], *, active: bool) -> None:
        ids_set = {int(x) for x in ids}
        if active:
            self.inactive_ids -= ids_set
        else:
            self.inactive_ids |= ids_set

    def add_points(self, df_points: pd.DataFrame) -> None:
        """
        Add new observations. Must already be canonical schema.
        """
        validate_canonical_df(df_points, allow_empty=False)
        if len(self.df_added) == 0:
            self.df_added = df_points.copy()
        else:
            self.df_added = pd.concat([self.df_added, df_points], ignore_index=True)

        # Update vis_sources to include any new sources
        for s in sorted(df_points[COL_SOURCE].unique()):
            if s not in self.vis_sources:
                self.vis_sources[s] = True

    @property
    def df_all(self) -> pd.DataFrame:
        if len(self.df_added) == 0:
            return self.df_raw
        return pd.concat([self.df_raw, self.df_added], ignore_index=True)

    @property
    def data_view(self) -> pd.DataFrame:
        """
        Derived dataframe for plotting/export, includes:
          - active
          - offset
          - flux_plot = flux + offset  (placeholder; you may want mag later)
        Applies visibility filters.
        """
        df = self.df_all.copy()

        # Visibility filters
        if self.vis_bands:
            df = df[df[COL_BAND].map(lambda b: self.vis_bands.get(str(b), False))]

        if self.vis_sources:
            df = df[df[COL_SOURCE].map(lambda s: self.vis_sources.get(str(s), False))]

        # Active mask
        inactive = self.inactive_ids
        if inactive:
            df[COL_ACTIVE] = ~df[COL_ID].astype(int).isin(inactive)
        else:
            df[COL_ACTIVE] = True

        # Offsets
        def _off(row: pd.Series) -> float:
            return float(self.offsets.get((row[COL_SOURCE], row[COL_BAND]), 0.0))

        if len(self.offsets):
            df[COL_OFFSET] = df.apply(_off, axis=1)
        else:
            df[COL_OFFSET] = 0.0

        df[COL_FLUX_PLOT] = df[COL_FLUX] + df[COL_OFFSET]

        return df

    def snapshot(self) -> Dict[str, Any]:
        """
        Export edit state (not full data) as JSON-serializable dict.
        """
        return {
            "schema_version": "1.0",
            "inactive_ids": sorted(int(x) for x in self.inactive_ids),
            "offsets": [
                {"source": s, "band": b, "value": float(v)}
                for (s, b), v in sorted(self.offsets.items())
            ],
            "vis_bands": {k: bool(v) for k, v in self.vis_bands.items()},
            "vis_sources": {k: bool(v) for k, v in self.vis_sources.items()},
        }

    def apply_snapshot(self, snap: Dict[str, Any]) -> None:
        """
        Apply snapshot to current session.
        """
        if str(snap.get("schema_version")) != "1.0":
            raise ValueError(f"Unsupported schema_version: {snap.get('schema_version')}")

        self.inactive_ids = {int(x) for x in snap.get("inactive_ids", [])}

        self.offsets = {}
        for item in snap.get("offsets", []):
            self.offsets[(str(item["source"]), str(item["band"]))] = float(item["value"])

        vb = snap.get("vis_bands")
        if isinstance(vb, dict):
            self.vis_bands.update({str(k): bool(v) for k, v in vb.items()})

        vs = snap.get("vis_sources")
        if isinstance(vs, dict):
            self.vis_sources.update({str(k): bool(v) for k, v in vs.items()})
