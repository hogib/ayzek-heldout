"""Pd gains only for a response flat across Pd's band (dataset.flatness).

Fixtures tests/fixtures/HA.AMPE.HHZ.xml and HL.ATH.HHZ.xml: the HHZ channel of
each station's StationXML in data/tune_greece_1/stationxml/ (metadata already
on disk, no request made; the other two channels removed, the file otherwise
verbatim). AMPE's sensitivity is stated at 0.05 Hz, below a 1 Hz corner, so its
response at 1 Hz is 283 times it; ATH is a flat broadband.
"""
from pathlib import Path

from obspy import read_inventory

from heldout import dataset

FIX = Path(__file__).parent / "fixtures"


# ---- Pd gains -------------------------------------------------------------------

def hhz(name):
    inv = read_inventory(str(FIX / name))
    return inv, inv[0][0].channels[0]


def test_ha_ampe_is_not_flat():
    _, c = hhz("HA.AMPE.HHZ.xml")
    why = dataset.flatness(c)
    assert why is not None and why.startswith("response not flat")
    assert "at 0.1 Hz" in why and "at 5 Hz" in why


def test_hl_ath_is_flat():
    _, c = hhz("HL.ATH.HHZ.xml")
    assert dataset.flatness(c) is None


def test_gains_writes_ath_and_refuses_ampe_with_the_reason():
    inv, _ = hhz("HL.ATH.HHZ.xml")
    inv += hhz("HA.AMPE.HHZ.xml")[0]
    chosen = [{"network": "HL", "station": "ATH", "location": ""},
              {"network": "HA", "station": "AMPE", "location": ""}]
    refused = []
    rows = dataset.gains(inv, chosen, refused)
    assert [r["station"] for r in rows] == ["ATH"]
    assert rows[0]["sensitivity"] == 394911000.0
    assert [(r["network"], r["station"], r["channel"]) for r in refused] == [("HA", "AMPE", "HHZ")]
    assert refused[0]["start"].startswith("2021-09-02T08:30:00")
    assert "not flat" in refused[0]["reason"]
    # Without a list to fill the refusal is silent but the same.
    assert dataset.gains(inv, chosen) == rows
