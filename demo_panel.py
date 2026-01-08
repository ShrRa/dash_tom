# demo_panel.py
import pandas as pd
import panel as pn

from dash_tvs.io import from_lsst_pickle_df
from dash_tvs.state import LCSession
from dash_tvs.panel_app import make_app

pn.extension("bokeh")

lc_file = '/home/alex/Data/Work/Sources/dash_dummy_data/lsst_RRLyr_with_diaSourceId.pkl'

df = pd.read_pickle(lc_file)  # <-- change this
canon = from_lsst_pickle_df(df)  # will generate mock diaSourceId if missing
sess = LCSession(canon)

app = make_app(sess)
app.servable()
