import pandas as pd

from dash_tvs.io import from_lsst_pickle_df, add_mock_diaSourceId
from dash_tvs.state import LCSession


def make_dummy_raw():
    df = pd.DataFrame(
        {
            "objectId": [11, 11, 11, 22, 22],
            "expMidptMJD": [1.0, 2.0, 3.0, 1.5, 2.5],
            "band": ["g", "g", "r", "g", "r"],
            "psfFlux": [10.0, 11.0, 9.0, 20.0, 19.0],
            "psfFluxErr": [1.0, 1.1, 0.9, 2.0, 1.9],
        }
    )
    df = add_mock_diaSourceId(df, object_col="objectId", time_col="expMidptMJD", source_name="LSST")
    canon = from_lsst_pickle_df(df, generate_mock_id_if_missing=False)
    return canon


def test_session_visibility_and_offsets():
    canon = make_dummy_raw()
    sess = LCSession(canon)

    # Initially all visible
    view0 = sess.data_view
    assert len(view0) == len(canon)

    # Hide band r
    sess.set_band_visible("r", False)
    view1 = sess.data_view
    assert (view1["band"] == "r").sum() == 0

    # Offset LSST g
    sess.set_offset("LSST", "g", 5.0)
    view2 = sess.data_view
    g = view2[view2["band"] == "g"]
    assert (g["flux_plot"] == g["flux"] + 5.0).all()


def test_toggle_active():
    canon = make_dummy_raw()
    sess = LCSession(canon)

    some_id = int(canon["diaSourceId"].iloc[0])
    sess.toggle_active([some_id], active=False)

    view = sess.data_view
    row = view[view["diaSourceId"] == some_id].iloc[0]
    assert row["active"] == False

    sess.toggle_active([some_id], active=True)
    view2 = sess.data_view
    row2 = view2[view2["diaSourceId"] == some_id].iloc[0]
    assert row2["active"] == True


def test_snapshot_roundtrip():
    canon = make_dummy_raw()
    sess = LCSession(canon)

    some_id = int(canon["diaSourceId"].iloc[1])
    sess.toggle_active([some_id], active=False)
    sess.set_offset("LSST", "g", -1.25)
    sess.set_band_visible("u", False)

    snap = sess.snapshot()

    sess2 = LCSession(canon)
    sess2.apply_snapshot(snap)

    assert some_id in sess2.inactive_ids
    assert sess2.offsets[("LSST", "g")] == -1.25
    assert sess2.vis_bands["u"] is False
