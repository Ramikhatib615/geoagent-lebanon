"""Tests for src/geoagent/tools.py and mcp_server.py (stdlib only). Run: python tests/test_tools.py"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, "..", "src", "geoagent")
sys.path.insert(0, SRC)
import tools, mcp_server


def test_normalisation_and_bilingual_match():
    assert tools.norm("الضَّاحية") == tools.norm("الضاحية")
    assert tools.norm("مزارع") == tools.norm("مزارع") and tools.norm("مدرسة") == tools.norm("مدرسه")
    en, _ = tools.resolve("dahieh"); ar, _ = tools.resolve("الضاحية الجنوبية")
    assert en and set(en) == set(ar), "English and Arabic names must resolve to the same blocks"


def test_counts_consistent_with_files():
    B = tools.load()["blocks"]; assert len(B) == 200
    lab = {"change": 0, "no_change": 0, "uncertain": 0}
    for b in B.values(): lab[b["label"]] += 1
    assert lab == {"change": 47, "no_change": 135, "uncertain": 18}, lab
    tot = sum(r["n_blocks"] for r in tools.list_places(limit=200)["places"]) + tools.list_places()["n_unnamed_blocks"]
    assert tot == 200
    s = tools.change_summary("Dahieh"); assert s["n_blocks"] == sum(s["labels"].values())


def test_weighted_estimate_matches_eval_results():
    ev = json.load(open(os.path.join(HERE, "..", "outputs", "eval", "eval_results_AI_consensus.json")))["prevalence"]
    for aoi in ("beirut", "mount_lebanon"):
        r = tools.area_estimate(aoi); assert abs(r["share_change_weighted"] - ev[aoi]) < 5e-4, (aoi, r["share_change_weighted"], ev[aoi])
        assert r["ci95_bootstrap"][0] < r["share_change_weighted"] < r["ci95_bootstrap"][1]


def test_not_found_and_suggestions():
    r = tools.change_summary("Hazmia"); assert r["found"] is False and "Hazmieh" in r["suggestions"]
    assert tools.block_evidence("E999")["found"] is False


def test_caveats_always_present_and_language():
    for r in (tools.change_summary("Dahieh"), tools.block_evidence("E002"), tools.uncertainty("E002"), tools.area_estimate("beirut"), tools.compare_places("Dahieh", "Hazmieh")):
        assert r["caveats"] and any("AI" in c for c in r["caveats"])
    ar = tools.change_summary("الضاحية"); assert any("؀" <= ch <= "ۿ" for ch in ar["message"]) and ar["caveats"] == tools.CAVEATS_AR


def test_uncertainty_flags_uncertain_and_adjudicated():
    B = tools.load()["blocks"]
    for i, b in B.items():
        u = tools.uncertainty(i)["blocks"][0]
        if b["label"] == "uncertain" or b["label_source"] == "adjudicated": assert u["defer_to_human"], i
        else: assert "label_uncertain" not in u["reasons"]


def test_compare_refuses_to_rank_small_samples():
    r = tools.compare_places("Bqaatouta", "Fanar"); assert r["ranking_allowed"] is False


def test_query_blocks_filters():
    assert tools.query_blocks()["n_blocks"] == 200
    a = tools.query_blocks(aoi="beirut", label="change")["n_blocks"] + tools.query_blocks(aoi="mount_lebanon", label="change")["n_blocks"]
    assert a == tools.query_blocks(label="change")["n_blocks"] == 47
    assert tools.query_blocks(place="Dahieh", label="change")["n_blocks"] == tools.change_summary("Dahieh")["labels"]["change"]
    assert tools.query_blocks(place="Nowhere")["found"] is False


def test_filters_accept_arabic_and_variants_R24():
    """R24: every categorical filter accepts Arabic and case/format variants (R13/R17 found silent empty results) and an unknown value is an explicit error."""
    same = [("label", "change", "تغيّر"), ("label", "no_change", "No change"), ("label_source", "agreed", "اتفق المصنّفان"),
            ("change_type", "quarry_earthworks", "محاجر / أعمال حفر وتسوية"), ("aoi", "mount_lebanon", "جبل لبنان"), ("stratum", "low", "منخفض"),
            ("governorate", "Mount Lebanon", "محافظة جبل لبنان"), ("governorate", "Keserwan", "كسروان - جبيل"), ("annotator_a", "uncertain", "غير مؤكد")]
    for f, en, ar in same:
        a, b = tools.query_blocks(**{f: en}), tools.query_blocks(**{f: ar})
        assert a["found"] and b["found"] and a["n_blocks"] == b["n_blocks"] > 0, (f, en, ar, a["n_blocks"], b.get("n_blocks"))
    assert tools.query_blocks(label="CHANGE")["n_blocks"] == 47 and tools.query_blocks(label="تغيّر")["message"].startswith("عدد")
    for f, v in (("label", "changd"), ("governorate", "North"), ("aoi", "Tripoli"), ("stratum", "very high")):
        r = tools.query_blocks(**{f: v}); assert r["found"] is False and r["error"] == "unknown_filter_value" and r["valid_values"], (f, v)
    assert tools.area_estimate(governorate="جبل لبنان")["share_change_weighted"] == tools.area_estimate(governorate="Mount Lebanon")["share_change_weighted"]
    assert tools.area_estimate(aoi="Tripoli")["error"] == "unknown_filter_value"
    assert tools.list_places(governorate="محافظة بيروت")["total_matching_places"] == tools.list_places(governorate="Beirut")["total_matching_places"] > 0
    assert tools.change_summary("Hazmiyeh")["suggestions"] == ["Hazmieh"], "R24: implausible suggestions are pruned"
    assert tools.change_summary("ضاهيه")["suggestions"] == ["Dahieh"], "R24: an Arabic misspelling of one word of a longer name gets a suggestion"
    assert tools.change_summary("Byblos")["suggestions"] == [] and tools.change_summary("Dahye")["suggestions"] == ["Dahieh"]


def test_blocks_near_index_exact_and_errors_R27():
    """R27: the grid index returns exactly the brute-force result; Arabic label filter; explicit errors."""
    import random
    B = tools.load()["blocks"]; lats = [b["centre_lat"] for b in B.values()]; lons = [b["centre_lon"] for b in B.values()]
    rng = random.Random(1)
    for _ in range(500):
        q = (rng.uniform(min(lats), max(lats)), rng.uniform(min(lons), max(lons)), rng.choice([0.3, 1, 3, 10]))
        assert tools._near_ids(*q, use_index=True) == tools._near_ids(*q, use_index=False)
    b = B["E141"]; r = tools.blocks_near(b["centre_lat"], b["centre_lon"], 2.0)
    assert r["found"] and r["blocks"][0]["id"] == "E141" and r["blocks"][0]["distance_km"] == 0.0 and r["n_blocks"] == sum(r["labels"].values())
    assert tools.blocks_near(b["centre_lat"], b["centre_lon"], 2.0, label="تغيّر")["n_blocks"] == r["labels"]["change"]
    assert tools.blocks_near(95, 35, 1)["error"] == "out_of_range" and tools.blocks_near("x", 35, 1)["error"] == "bad_coordinates"
    assert tools.blocks_near(b["centre_lat"], b["centre_lon"], 1, label="nope")["error"] == "unknown_filter_value"


def rpc(msgs):
    # R40: disable the tool-call audit log for this subprocess only (GEOAGENT_AUDIT_LOG="") so running the
    # test suite never writes to outputs/ as a side effect; a real launch of mcp_server.py without this
    # override still gets its default log path (see test_tool_audit_log.py for the logging behaviour itself).
    env = dict(os.environ, GEOAGENT_AUDIT_LOG="")
    p = subprocess.run([sys.executable, os.path.join(SRC, "mcp_server.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def test_audit_status_and_block_evidence_audit_fields():
    """The completed Appendix G audit, surfaced through the live tool layer: audit_status()'s aggregate summary
    and block_evidence()'s per-block human_audit field must agree with each other and with the audit's own result
    files, and must correctly separate the 13 pre-registered Rule 1 'certainty units' from the broader set of
    audited blocks whose reviewed label differs from the AI-consensus one."""
    a = tools.audit_status()
    assert a["found"] and a["n_audited"] == 80 and a["n_decided"] == 75 and a["n_interpretation_sensitive_undecided"] == 5
    assert a["rule1_certainty_units"]["n_units"] == 13
    assert a["rule1_certainty_units"]["flipped_block_ids"] == ["E137", "E199"], "Rule 1 fires on exactly these two certainty-unit blocks"
    assert set(a["rule1_certainty_units"]["flipped_block_ids"]) <= set(a["blocks_where_audited_label_differs_from_ai_consensus"])
    assert a["correlated_error_test"]["fires"] is True
    assert a["audited_headline_auc"]["conclusion"] == "not_supported_audit_sensitive"
    assert a["audited_area_estimate_km2"]["corrected"] == 56.6 and a["audited_area_estimate_km2"]["uncorrected"] == 82.1
    ar = tools.audit_status(lang="ar"); assert any("؀" <= ch <= "ۿ" for ch in ar["message"])

    for bid in ("E137", "E199"):
        be = tools.block_evidence(bid)
        assert be["human_audit"]["audited"] is True
        assert be["human_audit"]["human_final"] == "no_change" and be["label"] == "change"
        assert be["human_audit"]["differs_from_ai_consensus_label"] is True

    not_audited = [i for i in tools.load()["blocks"] if i not in tools._load_audit()][0]
    assert tools.block_evidence(not_audited)["human_audit"]["audited"] is False


def test_map_catalog_and_block_demo_R44():
    """R44: the executive defense map catalogue and the per-block defense summary must agree with audit_status()/
    block_evidence() on the two decisive Rule 1 flips (E137, E199) and the 5 still-contested interpretation-sensitive
    blocks, and must fail cleanly on an unknown id."""
    mc = tools.map_catalog()
    assert mc["found"] and mc["n_maps"] == 5
    ids = [m["id"] for m in mc["maps"]]
    assert ids == ["study_area_sampling_frame", "ai_consensus_change_labels", "human_audit_result",
                   "operational_deferral_map", "audit_corrected_interpretation"]
    for m in mc["maps"]:
        assert m["path_pdf"].endswith(".pdf") and m["path_png"].endswith(".png") and "exists" in m
        assert m["report_section"] and m["title"] and m["what_it_shows"] and m["talking_point"] and m["caveat"]
    mc_ar = tools.map_catalog(lang="ar")
    assert any("؀" <= ch <= "ۿ" for ch in mc_ar["maps"][0]["title"])

    for bid in ("E137", "E199"):
        d = tools.block_demo(bid)
        assert d["found"] and d["is_rule1_certainty_unit"] is True and d["is_rule1_pivotal_flip"] is True
        assert d["is_interpretation_sensitive"] is False
        assert d["ai_consensus_label"] == "change" and d["human_audit"]["human_final"] == "no_change"
        assert "audit_corrected_interpretation" in d["map_references"] or any("Audit-Corrected" in t for t in d["map_references"])

    for bid in ("E056", "E080", "E120", "E123", "E180"):
        d = tools.block_demo(bid)
        assert d["found"] and d["is_interpretation_sensitive"] is True, bid
        assert d["is_rule1_pivotal_flip"] is False, bid
        assert d["human_audit"]["audited"] is True and d["human_audit"]["human_final"] is None, bid
        assert "contested" in d["agreement_status"] or "متنازع" in d["agreement_status"], bid

    d_ar = tools.block_demo("E137", lang="ar")
    assert any("؀" <= ch <= "ۿ" for ch in d_ar["professor_friendly_explanation"])
    assert "change" not in d_ar["agreement_status"] and "no_change" not in d_ar["agreement_status"], \
        "R44 fix: the Arabic agreement_status must not embed raw English label words"

    r = tools.block_demo("E999")
    assert r["found"] is False and r["valid_id_pattern"] == "E001..E200"


def test_mcp_protocol_roundtrip():
    out = rpc([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
               {"jsonrpc": "2.0", "method": "notifications/initialized"},
               {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
               {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "change_summary", "arguments": {"place": "الضاحية الجنوبية"}}},
               {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
               {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "block_evidence", "arguments": {"wrong": 1}}}])
    assert len(out) == 5 and [o["id"] for o in out] == [1, 2, 3, 4, 5]
    assert out[0]["result"]["serverInfo"]["name"] == "geoagent-lebanon"
    assert {t["name"] for t in out[1]["result"]["tools"]} == set(tools.TOOLS)
    body = json.loads(out[2]["result"]["content"][0]["text"]); assert body["found"] and body["n_blocks"] == 20
    assert "error" in out[3] and out[4]["result"]["isError"] is True


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"): f(); print("PASS", n)
