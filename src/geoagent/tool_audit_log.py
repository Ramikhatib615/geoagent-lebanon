"""Tool-call audit log for the GeoAgent-Lebanon agent layer (R40, 2026-09-27).

Wraps tools.call() with a passive, best-effort audit trail: every invocation (tool name, arguments, a
compact summary of the result, latency, and a short tag for who called it) is appended as one JSON
line to a log file, so any answer the live agent (mcp_server.py), the CLI (tool_cli.py), or a
benchmark run gave can be traced back to the exact tool calls and raw results behind it.

Design principles (matching free_text_query.py's and agent_recovery.py's "does not modify tools.py"
rule for the frozen tool layer):
  - This module is a pure side-channel. audited_call(name, **kw) returns EXACTLY what
    tools.call(name, **kw) would have returned (same value, same exceptions), never something
    logging-shaped instead. Reading the result summary in the log can never differ from the real
    result the caller received.
  - Logging failures (disk full, permissions, a non-JSON-serialisable argument) are swallowed and
    never change the tool's return value or raise past this module -- an audit trail must not be able
    to break the thing it audits.
  - Logging is controlled entirely by the GEOAGENT_AUDIT_LOG environment variable (a file path, or ""
    to disable). This module never decides a default path itself; mcp_server.py and tool_cli.py each
    set one with os.environ.setdefault(...) at import time (so an operator or test harness can
    override or disable it first), and a caller that never sets it gets zero-overhead pass-through
    logging (one os.environ.get per call, otherwise identical to calling tools.call directly). This
    keeps ad-hoc scripts and unit tests log-free by default while the two real "agent layer" entry
    points log by default.
  - The log stores a *summary* of each result, not the full payload: block-level tables (up to 100
    rows) are common in tool results, and logging every one of them verbatim for every call over a
    long benchmark run would make the log itself an unbounded, slowly-duplicated copy of the reference
    dataset. Counts and key flags (found, error, n_blocks, ...) are what an audit actually needs to
    answer "did the agent get correct information for what it asked."

Usage:
    import tool_audit_log
    res = tool_audit_log.audited_call("change_summary", caller="mcp_server", place="Dahieh")
    # res is identical to tools.call("change_summary", place="Dahieh")

Reading the log back:
    tool_audit_log.read_log(path)                 -> list of parsed line dicts (skips unparsable lines)
    tool_audit_log.summarize_log(path)             -> {"n_calls", "by_tool", "by_caller", "n_errors", "n_not_found", "mean_latency_ms"}
"""
import json
import os
import threading
import time

_LOCK = threading.Lock()

_SUMMARY_KEYS = ("found", "error", "n_blocks", "n_deferred", "n_decided", "total_matching_places",
                  "ranking_allowed", "truncated", "share_change_weighted")
_LIST_KEYS = ("places", "blocks", "results")


def _log_path():
    return os.environ.get("GEOAGENT_AUDIT_LOG", "")


def _summarize_result(result):
    """A compact, size-bounded summary of a tool result -- enough to audit what the tool reported
    without duplicating block-level tables into the log."""
    if not isinstance(result, dict):
        return {"type": type(result).__name__}
    summary = {k: result[k] for k in _SUMMARY_KEYS if k in result}
    for key in _LIST_KEYS:
        v = result.get(key)
        if isinstance(v, list):
            summary["n_" + key] = len(v)
    if "block_ids" in result and isinstance(result["block_ids"], list):
        summary["n_block_ids"] = len(result["block_ids"])
    return summary


def _write_line(name, kw, caller, result, exc, latency_ms):
    path = _log_path()
    if not path:
        return
    line = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": name,
        "caller": caller,
        "latency_ms": latency_ms,
    }
    try:
        json.dumps(kw)  # cheap check that args are plain-JSON before trusting them in the real line
        line["args"] = kw
    except TypeError:
        line["args"] = {k: repr(v) for k, v in kw.items()}
    if exc is not None:
        line["exception"] = "%s: %s" % (type(exc).__name__, exc)
    else:
        line["result_summary"] = _summarize_result(result)
    try:
        text = json.dumps(line, ensure_ascii=False, default=str)
    except Exception as e:  # pragma: no cover - defensive: _summarize_result already returns plain types
        text = json.dumps({"ts": line["ts"], "tool": name, "caller": caller, "log_error": "unserialisable line: %s" % e})
    try:
        with _LOCK:
            d = os.path.dirname(os.path.abspath(path))
            if d:
                os.makedirs(d, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
    except Exception:
        pass  # logging must never break the tool call it is auditing


def audited_call(name, caller="unknown", **kw):
    """Same contract as tools.call(name, **kw): returns exactly what tools.call returns and raises
    exactly what it raises. caller is a short free-text tag ("mcp_server", "tool_cli", ...) recorded
    only in the log line, never passed through to the tool itself."""
    import tools  # imported lazily, mirroring free_text_query.py's zero-import-time-dependency style
    t0 = time.time()
    exc = None
    result = None
    try:
        result = tools.call(name, **kw)
        return result
    except Exception as e:
        exc = e
        raise
    finally:
        _write_line(name, kw, caller, result, exc, round((time.time() - t0) * 1000, 2))


def read_log(path):
    """Every parsable line of the log as a dict, in file order. Skips (does not raise on) any
    unparsable line, since a partially-written last line after a crash is expected, not corruption."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def summarize_log(path):
    """Aggregate counts over the log: total calls, per-tool and per-caller breakdown, how many
    resulted in an error or a not-found, and mean latency. Pure read, no side effects."""
    rows = read_log(path)
    by_tool, by_caller = {}, {}
    n_errors = n_not_found = 0
    latencies = []
    for r in rows:
        by_tool[r.get("tool")] = by_tool.get(r.get("tool"), 0) + 1
        by_caller[r.get("caller")] = by_caller.get(r.get("caller"), 0) + 1
        if "exception" in r or (r.get("result_summary") or {}).get("error"):
            n_errors += 1
        if (r.get("result_summary") or {}).get("found") is False:
            n_not_found += 1
        if isinstance(r.get("latency_ms"), (int, float)):
            latencies.append(r["latency_ms"])
    return {
        "n_calls": len(rows),
        "by_tool": by_tool,
        "by_caller": by_caller,
        "n_errors": n_errors,
        "n_not_found": n_not_found,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else _log_path()
    if not p:
        print("usage: python tool_audit_log.py <path-to-jsonl>  (or set GEOAGENT_AUDIT_LOG)")
        sys.exit(1)
    print(json.dumps(summarize_log(p), indent=1))
