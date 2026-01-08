from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn
from bokeh.models import CDSView, ColumnDataSource, GroupFilter, HoverTool
from bokeh.plotting import figure

from .state import LCSession
from .schema import COL_BAND, COL_FLUX_PLOT, COL_ID, COL_TIME

pn.extension("bokeh")

_BAND_PALETTE = {
    "u": "#56B4E9",
    "g": "#009E73",
    "r": "#D55E00",
    "i": "#CC79A7",
    "z": "#0072B2",
    "y": "#F0E442",
}


def _df_to_cds(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {
            COL_TIME: [], COL_FLUX_PLOT: [], COL_BAND: [], COL_ID: [],
            "active": [], "alpha": [], "line_alpha": []
        }

    active = df["active"].to_numpy(dtype=bool)
    return {
        COL_TIME: df[COL_TIME].to_numpy(),
        COL_FLUX_PLOT: df[COL_FLUX_PLOT].to_numpy(),
        COL_BAND: df[COL_BAND].astype(str).to_numpy(),
        COL_ID: df[COL_ID].to_numpy(),
        "active": active,
        "alpha": np.where(active, 0.85, 0.10),
        "line_alpha": np.where(active, 0.60, 0.10),
    }


class LCVizApp:
    def __init__(self, session: LCSession):
        self.session = session

        df0 = self.session.data_view.sort_values(COL_TIME)
        self.cds = ColumnDataSource(_df_to_cds(df0))

        self.plot = self._make_figure(self.cds)

        self.btn_deactivate = pn.widgets.Button(name="Deactivate selected", button_type="danger")
        self.btn_reactivate = pn.widgets.Button(name="Reactivate selected", button_type="success")
        self.btn_clear = pn.widgets.Button(name="Clear selection", button_type="default")
        self.status = pn.pane.Markdown("", sizing_mode="stretch_width")
        self.last_action = ""


        self.btn_deactivate.on_click(self._deactivate)
        self.btn_reactivate.on_click(self._reactivate)
        self.btn_clear.on_click(self._clear_selection)

        self.cds.selected.on_change("indices", self._on_selection_change)
        self.status.object = "No points selected."


        self.layout = pn.Column(
            pn.pane.Bokeh(self.plot, sizing_mode="stretch_width"),
            pn.Row(self.btn_deactivate, self.btn_reactivate, self.btn_clear, sizing_mode="stretch_width"),
            self.status,
            sizing_mode="stretch_width",
        )

    def _make_figure(self, source: ColumnDataSource):
        p = figure(
            height=420,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,box_select,lasso_select,tap,reset,save",
            active_scroll="wheel_zoom",
            x_axis_label="MJD",
            y_axis_label="Flux (offset applied)",
        )

        ugrizy = ["u", "g", "r", "i", "z", "y"]
        bands_present = list(dict.fromkeys(source.data.get(COL_BAND, [])))
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
                fill_color=color,
                line_color=color,
                fill_alpha="alpha",
                line_alpha="line_alpha",
                legend_label=b,
                # Selection highlight (works regardless of active/inactive)
                selection_fill_alpha=1.0,
                selection_line_alpha=1.0,
                selection_line_width=3,
                # Non-selected points stay as they were (respecting alpha columns)
                nonselection_fill_alpha="alpha",
                nonselection_line_alpha="line_alpha",
            )
            renderers.append(r)

        p.legend.title = "Band"
        p.legend.click_policy = "hide"

        p.add_tools(
            HoverTool(
                renderers=renderers,
                tooltips=[
                    ("diaSourceId", f"@{COL_ID}"),
                    ("band", f"@{COL_BAND}"),
                    ("mjd", f"@{COL_TIME}{{0.000}}"),
                    ("flux_plot", f"@{COL_FLUX_PLOT}{{0.000}}"),
                    ("active", "@active"),
                ],
                formatters={f"@{COL_TIME}": "printf", f"@{COL_FLUX_PLOT}": "printf"},
            )
        )
        return p

    def _refresh(self):
        dfv = self.session.data_view.sort_values(COL_TIME)
        self.cds.data = _df_to_cds(dfv)

    def _selected_ids(self) -> list[int]:
        idxs = list(self.cds.selected.indices)
        if not idxs:
            return []
        ids = self.cds.data[COL_ID]
        return [int(ids[i]) for i in idxs]

    def _deactivate(self, _=None):
        ids = self._selected_ids()
        if not ids:
            self.status.object = "No points selected."
            return
        self.session.toggle_active(ids, active=False)
        self.last_action = f"Deactivated {len(ids)} point(s)."
        self._refresh()
        self.cds.selected.indices = []
        self._update_status()

    def _reactivate(self, _=None):
        ids = self._selected_ids()
        if not ids:
            self.status.object = "No points selected."
            return
        self.session.toggle_active(ids, active=True)
        self.last_action = f"Reactivated {len(ids)} point(s)."
        self._refresh()
        self.cds.selected.indices = []
        self._update_status()

    def _clear_selection(self, _=None):
        self.cds.selected.indices = []

    def _on_selection_change(self, attr, old, new):
        self._update_status()

    def _update_status(self):
        n = len(self.cds.selected.indices)
        sel = "No points selected." if n == 0 else (f"{n} points selected." if n != 1 else "1 point selected.")
        if self.last_action:
            self.status.object = f"{self.last_action}\n\n{sel}"
        else:
            self.status.object = sel



def make_app(session: LCSession) -> pn.Column:
    return LCVizApp(session).layout
