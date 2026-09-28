"""Command-line access to the GeoAgent-Lebanon tool layer (R24): the same functions and schemas mcp_server.py exposes, one call per run.
Usage:  python3 src/geoagent/tool_cli.py list                       -> tool names, descriptions and argument schemas (JSON)
        python3 src/geoagent/tool_cli.py <tool> '<json arguments>'  -> the tool's JSON result
Used to run benchmark v4 against the current tools.py without restarting the MCP client that has the server loaded.

R40 (2026-09-27): logged through tool_audit_log.audited_call (caller="tool_cli"), same GEOAGENT_AUDIT_LOG default
as mcp_server.py, so a benchmark run using this CLI shows up in the same audit trail as live agent sessions.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("GEOAGENT_AUDIT_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs", "agent_tool_audit_log.jsonl"))
import tools
import tool_audit_log

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        print(json.dumps({n: {"description": d, "arguments": p, "required": r} for n, (_, d, p, r) in tools.TOOLS.items()}, ensure_ascii=False, indent=1))
        sys.exit(0)
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        print(json.dumps(tool_audit_log.audited_call(name, caller="tool_cli", **args), ensure_ascii=False, indent=1))
    except TypeError as e:
        print(json.dumps({"error": "bad arguments: %s" % e}))
