# demo_panel.py
# This is a standalone demo of the panel app for local testing without Django integration. Can be run with `panel serve demo_panel.py`
import pandas as pd
import panel as pn

from dash_tvs.io import from_lsst_pickle_df
from dash_tvs.state import LCSession
from dash_tvs.panel_app import make_app

pn.extension("bokeh")

lc_file = '/home/alex/Data/Work/Sources/dash_dummy_data/lsst_RRLyr_with_diaSourceId.pkl'

df = pd.read_pickle(lc_file) 
oid = df['objectId'].unique()[0]
print(len(df)) 
df =df[df['objectId']==oid][:10].reset_index(drop=True)
print(len(df))  # single source for demo
canon = from_lsst_pickle_df(df)
sess = LCSession(canon)

app = make_app(sess)
app.servable()
