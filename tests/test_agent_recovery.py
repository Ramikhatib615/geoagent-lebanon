"""Tests for src/geoagent/agent_recovery.py (R27). Run: python tests/test_agent_recovery.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "src", "geoagent"))
import tools, agent_recovery as AR


def test_place_suggestion_is_used_and_surfaced():
    r = AR.call_with_recovery("change_summary", place="Dahye")
    assert r["found"] and r["recovered"] and r["recovery"][0]["to"] == "Dahieh" and "Dahye" in r["recovery_note"]
    assert r["n_blocks"] == tools.change_summary("Dahieh")["n_blocks"]


def test_no_recovery_when_nothing_close():
    r = AR.call_with_recovery("change_summary", place="Byblos")
    assert r["found"] is False and r["recovered"] is False and r["recovery"] == []


def test_filter_value_single_suggestion():
    r = AR.call_with_recovery("query_blocks", label="changd")
    assert r.get("error") == "unknown_filter_value" or r["recovered"]          # two suggestions -> not guessed
    r2 = AR.call_with_recovery("query_blocks", stratum="very high")
    assert r2["recovered"] and r2["filters_canonical"]["stratum"] == "high" and r2["recovery"][0]["from"] == "very high"


def test_radius_and_box_expand_and_bad_args():
    b = tools.load()["blocks"]["E141"]
    r = AR.call_with_recovery("blocks_near", lat=b["centre_lat"] + 0.01, lon=b["centre_lon"], radius_km=0.2)
    assert r["recovered"] and r["n_blocks"] > 0 and all(s["changed"] == "radius_km" for s in r["recovery"])
    r = AR.call_with_recovery("query_blocks", min_lat=b["centre_lat"] + 0.001, max_lat=b["centre_lat"] + 0.002, min_lon=b["centre_lon"] + 0.001, max_lon=b["centre_lon"] + 0.002)
    assert r["recovered"] and r["n_blocks"] > 0
    r = AR.call_with_recovery("block_evidence", block_id="E141", colour="red")
    assert r["found"] and r["recovery"][0]["changed"] == "arguments"


def test_success_is_untouched():
    r = AR.call_with_recovery("change_summary", place="Dahieh")
    assert r["recovered"] is False and r["recovery"] == [] and "recovery_note" not in r


if __name__ == "__main__":
    n = 0
    for k, f in sorted(globals().items()):
        if k.startswith("test_"): f(); print("PASS", k); n += 1
    print(n, "passed")
