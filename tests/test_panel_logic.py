"""Tests of the QGIS panel logic (no QGIS needed; standard library only). Run: python tests/test_panel_logic.py"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "geoagent"))
import tools
import panel_logic as PL
import free_text_query as FTQ


def test_choices_match_data():
    c = PL.enum_choices(tools.load()["blocks"])
    assert c["aoi"] == ["", "beirut", "mount_lebanon"]
    assert "new_construction" in c["change_type"] and "greenhouse_agri" in c["change_type"]
    assert c["label_source"] == ["", "adjudicated", "agreed"]
    assert c["governorate"][0] == "" and len(c["governorate"]) == 4


def test_parse_values_ok_and_errors():
    p, req = tools.TOOLS["query_blocks"][2], tools.TOOLS["query_blocks"][3]
    kw, errs = PL.parse_values(p, req, {"label": "change", "annotators_disagree": "true", "min_lat": "33,8", "max_lat": "34"})
    assert not errs and kw == {"label": "change", "annotators_disagree": True, "min_lat": 33.8, "max_lat": 34.0}
    kw, errs = PL.parse_values(p, req, {"min_lat": "34", "max_lat": "33"})
    assert any("smaller" in e for e in errs)
    kw, errs = PL.parse_values(p, req, {"min_lat": "abc"})
    assert errs and "number" in errs[0]
    p, req = tools.TOOLS["list_places"][2], tools.TOOLS["list_places"][3]
    assert PL.parse_values(p, req, {"limit": "x"})[1] and PL.parse_values(p, req, {"limit": "0"})[1]
    assert not PL.parse_values(p, req, {"limit": "5"})[1]
    p, req = tools.TOOLS["change_summary"][2], tools.TOOLS["change_summary"][3]
    assert PL.parse_values(p, req, {"place": "  "})[1] == ["'place' is required."]
    p, req = tools.TOOLS["block_evidence"][2], tools.TOOLS["block_evidence"][3]
    assert PL.parse_values(p, req, {"block_id": "67"})[1] and not PL.parse_values(p, req, {"block_id": "e067"})[1]


def test_collect_ids():
    r = tools.call("compare_places", place_a="Dahieh", place_b="Hazmieh")
    ids = PL.collect_ids(r, [])
    assert len(ids) == 31 and ids == sorted(set(ids)) and all(PL.ID_RE.fullmatch(i) for i in ids)
    assert PL.collect_ids(tools.call("block_evidence", block_id="E067"), []) == ["E067"]
    assert PL.collect_ids({"x": "E12", "y": ["E001"]}, []) == []


def test_render_english_and_arabic():
    r = tools.call("change_summary", place="الضاحية الجنوبية", lang="ar")
    h = PL.render_answer(r, PL.collect_ids(r, []))
    assert "الكتل" in h and "dir='auto'" in h and "Caveats" in h and "Blocks (20)" in h
    r = tools.call("uncertainty", place="Dahieh")
    h = PL.render_answer(r, [])
    assert "<table" in h and "E067" in h and "annotators_disagreed_then_adjudicated" in h
    r = tools.call("list_places", limit=4)
    assert "Dahieh" in PL.render_answer(r, [])


def test_localised_duplicates_hidden():
    r = tools.call("block_evidence", block_id="E067", lang="ar")
    h = PL.render_answer(r, ["E067"])
    assert "label localised" in h and ">label<" not in h


def test_render_not_found_and_error_and_html_escape():
    h = PL.render_answer(tools.call("change_summary", place="Atlantis"), [])
    assert "Did you mean" in h and "Halat" in h
    assert "Error" in PL.render_answer({"error": "boom <b>"}, []) and "&lt;b&gt;" in PL.render_answer({"error": "boom <b>"}, [])
    assert "<script>" not in PL.render_answer({"message": "<script>alert(1)</script>"}, [])


def test_zero_hint_and_pretty():
    assert PL.zero_hint("query_blocks", tools.call("query_blocks", aoi="beirut", change_type="vegetation_change"))   # a genuine empty selection
    assert not PL.zero_hint("query_blocks", tools.call("query_blocks", label="CHANGE"))                           # R24: case variants now resolve
    assert not PL.zero_hint("query_blocks", tools.call("query_blocks", label="change"))
    assert PL.pretty(None) == "—" and PL.pretty(True) == "yes" and PL.pretty(0.23500) == "0.235"
    assert PL.pretty({"place_en": "A", "place_ar": "ب"}) == "A (ب)"


def test_free_text_panel_integration():
    """R40: the panel's free-text box (qgis_agent_panel.Panel.ask_free_text) parses a question with
    free_text_query.parse_query(), fills the same form fields panel_logic already validates, and calls
    the same tools.call() every other entry point uses. Simulates that whole path headlessly (no QGIS
    needed) for a representative EN/AR sample, exactly as ask_free_text() does it."""
    place_index = sorted({n for b in tools.load()["blocks"].values() for n in (b.get("place_en"), b.get("place_ar")) if n})
    cases = [
        ("how has Dahieh changed since 2018?", "change_summary", True),
        ("compare Byblos with Baabda", "compare_places", False),  # Byblos isn't in the named sample -> graceful not-found
        ("what share of Beirut changed", "area_estimate", True),
        ("evidence for block E067", "block_evidence", True),
        ("which blocks need review in Hazmieh", "uncertainty", True),
        ("list places in Mount Lebanon Governorate", "list_places", True),
        ("كيف تغيرت بيروت", "change_summary", True),
        ("قارن بين حازمية والدورة", "compare_places", True),
    ]
    for text, expect_tool, expect_found in cases:
        r = FTQ.parse_query(text, place_index=place_index)
        assert r.tool == expect_tool, (text, r.tool, expect_tool)
        fn, desc, params, req = tools.TOOLS[r.tool]
        raw = {k: str(v) for k, v in r.args.items()}  # mirrors reading text back out of QLineEdit/QComboBox
        kw, errs = PL.parse_values(params, req, raw)
        assert not errs, (text, errs)
        res = tools.call(r.tool, **kw)
        assert res.get("found", True) is expect_found, (text, res.get("found"), res.get("message"))
        html = PL.render_answer(res, PL.collect_ids(res, []))
        assert html and "<" in html
    assert FTQ.parse_query("asdkjaslkdj random gibberish", place_index=place_index).tool is None


def test_dataset_stats_numbers():
    """R40: the panel's live-stats widget recomputes label counts from tools.load()['blocks'] directly
    (rather than importing a shared helper, since it's a tiny QGIS-side readout) -- pin the exact numbers
    here so a future data change is caught, not just silently shown differently in the panel."""
    B = tools.load()["blocks"]
    lab = {"change": 0, "no_change": 0, "uncertain": 0}
    for b in B.values():
        lab[b["label"]] += 1
    assert len(B) == 200
    assert lab == {"change": 47, "no_change": 135, "uncertain": 18}
    assert lab["change"] + lab["no_change"] == 182  # matches query_blocks' own n_decided (see SELF_TESTS)


def test_self_test_passes():
    ok, n, fails = PL.self_test(tools)
    assert ok == n and not fails, fails


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name); n += 1
    print("%d passed" % n)
