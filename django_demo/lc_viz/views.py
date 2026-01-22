from __future__ import annotations

from bokeh.embed import server_document
from django.http import HttpRequest
from django.shortcuts import render

LC_FILE = '/home/alex/Data/Work/Sources/dash_dummy_data/lsst_RRLyr_with_diaSourceId.pkl'

# ---- Django view: regular page, embeds the app script ----

def lc_page(request):
    script = server_document(request.build_absolute_uri())
    return render(request, "lc_viz/page.html", {"script": script})



# ---- Bokeh/Panel handler: this runs inside the embedded Bokeh server ----

def lc_panel_app(doc):
    import pandas as pd
    import panel as pn

    from dash_tvs.io import from_lsst_pickle_df
    from dash_tvs.state import LCSession
    from dash_tvs.panel_app import make_app

    pn.extension("bokeh")

    # TODO: replace with real data fetch (DB / API) later
    df = pd.read_pickle(LC_FILE)
    oid = df['objectId'].unique()[2]
    df =df[df['objectId']==oid].reset_index(drop=True)
    canon = from_lsst_pickle_df(df)
    sess = LCSession(canon)

    layout = make_app(sess)
    layout.server_doc(doc)
