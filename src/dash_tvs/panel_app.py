# src/dash_tvs/panel_app.py
from __future__ import annotations

import pandas as pd
import panel as pn
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.models import CategoricalColorMapper
from bokeh.models import CDSView, GroupFilter
from bokeh.palettes import Category10
from bokeh.plotting import figure

from .state import LCSession
from .schema import (
    COL_BAND,
    COL_FLUX_PLOT,
    COL_ID,
    COL_TIME,
)

pn.extension("bokeh")

_BAND_PALETTE = {
    "u": "#56B4E9",
    "g": "#009E73",
    "r": "#D55E00",
    "i": "#CC79A7",
    "z": "#0072B2",
    "y": "#F0E442",
}

def _make_figure(source: ColumnDataSource):
    p = figure(
        height=420,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
        x_axis_label="MJD",
        y_axis_label="Flux (offset applied)",
    )

    # Determine bands present in the current CDS, enforce ugrizy order
    bands_present = list(dict.fromkeys(source.data.get(COL_BAND, [])))  # preserve appearance order
    ugrizy = ["u", "g", "r", "i", "z", "y"]
    bands_present = [b for b in ugrizy if b in set(bands_present)] + [
        b for b in sorted(set(bands_present)) if b not in set(ugrizy)
    ]

    renderers = []
    for b in bands_present:
        view = CDSView(filter=GroupFilter(column_name=COL_BAND, group=b))
        color = _BAND_PALETTE.get(b, "#999999")

        r = p.circle(
            x=COL_TIME,
            y=COL_FLUX_PLOT,
            source=source,
            view=view,
            size=5,
            line_alpha=0.6,
            fill_alpha=0.8,
            fill_color=color,
            line_color=color,
            legend_label=b,
        )
        renderers.append(r)

    p.legend.title = "Band"
    p.legend.click_policy = "hide"

    # Hover over all band renderers
    p.add_tools(
        HoverTool(
            renderers=renderers,
            tooltips=[
                ("diaSourceId", f"@{COL_ID}"),
                ("band", f"@{COL_BAND}"),
                ("mjd", f"@{COL_TIME}{{0.000}}"),
                ("flux_plot", f"@{COL_FLUX_PLOT}{{0.000}}"),
            ],
            formatters={f"@{COL_TIME}": "printf", f"@{COL_FLUX_PLOT}": "printf"},
        )
    )

    return p




def _df_to_cds(df: pd.DataFrame) -> dict:
    # Bokeh CDS wants plain sequences; keep only what we plot + hover.
    if len(df) == 0:
        return {COL_TIME: [], COL_FLUX_PLOT: [], COL_BAND: [], COL_ID: []}
    return {
        COL_TIME: df[COL_TIME].to_numpy(),
        COL_FLUX_PLOT: df[COL_FLUX_PLOT].to_numpy(),
        COL_BAND: df[COL_BAND].astype(str).to_numpy(),
        COL_ID: df[COL_ID].to_numpy(),
    }


def make_app(session: LCSession) -> pn.Column:
    """
    Build a minimal Panel app:
      - scatter plot (mjd vs flux_plot)
      - band toggles (MultiChoice)
    """
    # Determine available bands from data (don’t assume ugrizy all present)
    df0 = session.data_view
    available_bands = sorted(df0[COL_BAND].unique().tolist()) if len(df0) else []
    default_bands = [b for b in available_bands if session.vis_bands.get(b, True)]

    cds = ColumnDataSource(_df_to_cds(df0.sort_values(COL_TIME)))
    p = _make_figure(cds)

    def _refresh():
        dfv = session.data_view.sort_values(COL_TIME)
        cds.data = _df_to_cds(dfv)

    layout = pn.Column(
        pn.pane.Bokeh(p, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )
    return layout
