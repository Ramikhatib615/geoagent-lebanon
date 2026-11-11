"""Minimal dependency-free MCP server (stdio, JSON-RPC 2.0, newline-delimited) exposing the tools in tools.py.
Implements initialize, ping, tools/list, tools/call and notifications/initialized (protocol 2024-11-05, compatible with 2025-03-26 clients).
Run:  python src/geoagent/mcp_server.py      (register in an MCP client as a stdio server)

R40 (2026-09-27): every tools/call is passed through tool_audit_log.audited_call rather than tools.call
directly, so every real agent session is logged to GEOAGENT_AUDIT_LOG (default: outputs/agent_tool_audit_log.jsonl,
relative to the repo root; set the env var to another path, or to "" to disable, before launching this server).
This changes nothing about what a call returns -- see tool_audit_log.py's own docstring for the "never change
the result" guarantee -- it only adds a passive record of what was asked and what came back.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools
import tool_audit_log
import human_ref_tools   # 11 read-only tools over the 300 human-reviewed blocks
import osm_tools_v25     # 8 read-only historical-OpenStreetMap tools

PROTOCOL = "2024-11-05"
INFO = {"name": "geoagent-lebanon", "version": "0.5.0"}


def tool_list():
    out = []
    for n, (fn, desc, props, req) in tools.TOOLS.items():
        out.append({"name": n, "description": desc, "inputSchema": {"type": "object", "properties": props, "required": req}})
    return out


def handle(msg):
    """Return a response dict for a request, or None for notifications."""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:                                   # notification
        return None
    def ok(r): return {"jsonrpc": "2.0", "id": mid, "result": r}
    def err(c, m): return {"jsonrpc": "2.0", "id": mid, "error": {"code": c, "message": m}}
    if method == "initialize":
        v = params.get("protocolVersion") or PROTOCOL
        return ok({"protocolVersion": v if v in ("2024-11-05", "2025-03-26", "2025-06-18") else PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": INFO})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": tool_list()})
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in tools.TOOLS:
            return err(-32602, "unknown tool: %s" % name)
        try:
            res = tool_audit_log.audited_call(name, caller="mcp_server", **args)
            return ok({"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}], "isError": False})
        except TypeError as e:
            return ok({"content": [{"type": "text", "text": "invalid arguments: %s" % e}], "isError": True})
        except Exception as e:                        # tool errors are reported to the model, not raised as protocol errors
            return ok({"content": [{"type": "text", "text": "tool error: %s" % e}], "isError": True})
    return err(-32601, "method not found: %s" % method)


def main():
    # Set only when actually launched as a server (not on import, so importing this module for tests
    # -- test_tools.py exercises handle() directly -- never activates real logging as a side effect).
    os.environ.setdefault("GEOAGENT_AUDIT_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs", "agent_tool_audit_log.jsonl"))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            r = handle(json.loads(line))
        except json.JSONDecodeError:
            r = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if r is not None:
            sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
