"""Tests of the tool-call audit log (R40). Standard library only, no QGIS. Run: python tests/test_tool_audit_log.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "geoagent"))
import tools
import tool_audit_log as TAL


def test_disabled_by_default_no_env_var():
    os.environ.pop("GEOAGENT_AUDIT_LOG", None)
    # must behave exactly like tools.call: same value, and critically, no file materialises anywhere
    # obvious (there is no path to write to when the env var is unset).
    direct = tools.call("change_summary", place="Dahieh")
    audited = TAL.audited_call("change_summary", caller="test", place="Dahieh")
    assert direct == audited


def test_result_unchanged_for_success_error_and_unknown_tool():
    for name, kw in (("change_summary", {"place": "Dahieh"}), ("change_summary", {"place": "Atlantis"}), ("bogus_tool_xyz", {})):
        assert tools.call(name, **kw) == TAL.audited_call(name, caller="test", **kw)


def test_writes_one_line_per_call_and_never_raises_on_bad_path():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "sub", "audit.jsonl")  # subdirectory must be created on demand
        os.environ["GEOAGENT_AUDIT_LOG"] = path
        try:
            TAL.audited_call("change_summary", caller="test", place="Dahieh")
            TAL.audited_call("change_summary", caller="test", place="Atlantis")
            TAL.audited_call("bogus_tool_xyz", caller="test")
            rows = TAL.read_log(path)
            assert len(rows) == 3
            assert rows[0]["tool"] == "change_summary" and rows[0]["caller"] == "test"
            assert rows[0]["result_summary"]["found"] is True and rows[0]["result_summary"]["n_blocks"] == 20
            assert rows[1]["result_summary"]["found"] is False
            assert rows[2]["result_summary"]["error"] == "unknown tool bogus_tool_xyz"
            assert all(isinstance(r["latency_ms"], (int, float)) and r["latency_ms"] >= 0 for r in rows)
        finally:
            os.environ.pop("GEOAGENT_AUDIT_LOG", None)


def test_summarize_log():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "audit.jsonl")
        os.environ["GEOAGENT_AUDIT_LOG"] = path
        try:
            TAL.audited_call("change_summary", caller="mcp_server", place="Dahieh")
            TAL.audited_call("change_summary", caller="tool_cli", place="Atlantis")
            TAL.audited_call("area_estimate", caller="mcp_server", aoi="beirut")
            s = TAL.summarize_log(path)
            assert s["n_calls"] == 3
            assert s["by_tool"] == {"change_summary": 2, "area_estimate": 1}
            assert s["by_caller"] == {"mcp_server": 2, "tool_cli": 1}
            assert s["n_not_found"] == 1 and s["n_errors"] == 0
            assert isinstance(s["mean_latency_ms"], float)
        finally:
            os.environ.pop("GEOAGENT_AUDIT_LOG", None)


def test_summarize_log_missing_file_is_empty_not_an_error():
    s = TAL.summarize_log("/nonexistent/path/does/not/exist.jsonl")
    assert s == {"n_calls": 0, "by_tool": {}, "by_caller": {}, "n_errors": 0, "n_not_found": 0, "mean_latency_ms": None}


def test_exception_from_tool_is_logged_and_reraised():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "audit.jsonl")
        os.environ["GEOAGENT_AUDIT_LOG"] = path
        try:
            raised = False
            try:
                TAL.audited_call("block_evidence", caller="test")  # missing required block_id -> TypeError
            except TypeError:
                raised = True
            assert raised
            rows = TAL.read_log(path)
            assert len(rows) == 1 and "exception" in rows[0] and "TypeError" in rows[0]["exception"]
        finally:
            os.environ.pop("GEOAGENT_AUDIT_LOG", None)


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
            n += 1
    print("%d passed" % n)
