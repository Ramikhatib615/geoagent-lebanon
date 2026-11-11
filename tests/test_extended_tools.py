"""Tests of the 30-tool registry, the MCP round trip and the 19 human-reference / historical-OSM tools.
The restricted datasets are not in the repository, so these tests (a) check the graceful "not available" answer
and (b) exercise every tool against SYNTHETIC fixtures (tests/fixtures), in a subprocess with the two
environment variables set. Run: python tests/test_extended_tools.py   (or: pytest)"""
import hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, "..", "src", "geoagent"); FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, SRC)
import tools, mcp_server  # noqa: E402  (mcp_server registers the human-reference and OSM tools)

EXTENDED = ["human_block_lookup", "human_label_provenance", "human_reviewer_agreement", "human_unresolved", "model_vs_human",
            "human_regional_performance", "building_footprint_evidence", "damage_claim_check", "human_query_blocks",
            "human_blocks_near", "human_dataset_scope", "osm_block_history", "osm_mapping_vs_physical", "osm_building_free_status",
            "osm_vs_scores", "osm_region_coverage", "osm_contradictions", "osm_physical_verification", "osm_zero_footprint_summary"]
ARGS = {"human_block_lookup": {"block_id": "N900_900"}, "human_label_provenance": {"block_id": "N900_900"}, "model_vs_human": {"block_id": "N900_900"},
        "building_footprint_evidence": {"block_id": "N900_900"}, "damage_claim_check": {"place": "Beirut"},
        "human_blocks_near": {"lat": 33.9, "lon": 35.6, "radius_km": 30}, "osm_block_history": {"block_id": "N900_900"},
        "osm_building_free_status": {"block_id": "N900_900"}, "osm_vs_scores": {"kind": "osm_increase_low_spectral"}}
NEEDS_FILE = [n for n in EXTENDED if n not in ("osm_mapping_vs_physical", "osm_physical_verification", "damage_claim_check")]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _run_with_fixtures(code):
    env = dict(os.environ, GEOAGENT_HUMAN_REF=os.path.join(FIX, "human_ref_synthetic.csv"),
               GEOAGENT_OSM_HIST=os.path.join(FIX, "block_osm_features_synthetic.csv"), GEOAGENT_AUDIT_LOG="", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r)\n%s" % (SRC, code)], env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout)


def test_registry_has_30_documented_tools():
    assert len(tools.TOOLS) == 30, len(tools.TOOLS)
    assert all(n in tools.TOOLS for n in EXTENDED)
    for name, (fn, desc, props, req) in tools.TOOLS.items():
        assert callable(fn) and isinstance(desc, str) and len(desc) > 20, name
        assert isinstance(props, dict) and all(k in props for k in req), name


def test_mcp_round_trip_lists_and_calls():
    init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
    assert init["result"]["serverInfo"]["name"] == "geoagent-lebanon"
    listed = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert len(listed) == 30 and all(t["inputSchema"]["type"] == "object" for t in listed)
    assert mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "no_such_tool"}})["error"]["code"] == -32602
    assert mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_no_write_tool_exists():
    banned = {"write", "update", "delete", "set", "edit", "create", "insert", "relabel", "save"}
    assert not [n for n in tools.TOOLS if banned & set(n.split("_"))]


def test_restricted_data_absent_gives_structured_answer():
    if os.path.exists(os.path.join(HERE, "..", "data", "human_ref", "human_ref_300.csv")) or os.environ.get("GEOAGENT_HUMAN_REF"):
        return  # the restricted file is present locally: nothing to check here
    for n in NEEDS_FILE:
        r = tools.call(n, **ARGS.get(n, {}))
        assert r["found"] is False and r["available"] is False and "docs/data-availability.md" in r["error"], n
    assert tools.call("osm_mapping_vs_physical")["answer"].startswith("No.")
    assert tools.call("damage_claim_check", place="Beirut")["can_support_damage_claim"] is False


def test_every_extended_tool_runs_on_synthetic_fixtures_and_is_read_only():
    before = [_sha(os.path.join(FIX, f)) for f in ("human_ref_synthetic.csv", "block_osm_features_synthetic.csv")]
    out = _run_with_fixtures("import json, tools, mcp_server\nA=%r\nprint(json.dumps({n: tools.call(n, **A.get(n, {})) for n in %r}, ensure_ascii=False))" % (ARGS, EXTENDED))
    for n in EXTENDED:
        assert isinstance(out[n], dict) and "available" not in out[n], n
    assert out["human_dataset_scope"]["n_blocks"] == 96 and out["human_block_lookup"]["block_id"] == "N900_900"
    assert out["osm_building_free_status"]["verified_building_free"] is False
    assert out["osm_zero_footprint_summary"]["verified_building_free"] == 0
    assert out["osm_physical_verification"]["status"] == "PENDING"
    assert before == [_sha(os.path.join(FIX, f)) for f in ("human_ref_synthetic.csv", "block_osm_features_synthetic.csv")]


def test_bilingual_and_error_paths_on_synthetic_fixtures():
    out = _run_with_fixtures("import json, tools, mcp_server\nprint(json.dumps({'ar': tools.call('human_dataset_scope', lang='ar'), 'bad': tools.call('human_block_lookup', block_id='N001_001'),"
                             "'far': tools.call('human_blocks_near', lat=10.0, lon=10.0, radius_km=5), 'gov': tools.call('human_query_blocks', governorate='\\u0628\\u064a\\u0631\\u0648\\u062a')}, ensure_ascii=False))")
    assert any("؀" <= ch <= "ۿ" for ch in json.dumps(out["ar"], ensure_ascii=False))
    assert out["bad"]["found"] is False and out["far"]["found"] is False
    assert out["gov"]["found"] is True and out["gov"]["n_blocks"] == 12


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print("%d passed" % len(fns))
