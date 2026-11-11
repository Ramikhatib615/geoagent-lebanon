# Architecture

```
                         ┌────────────────────────────┐
                         │   outputs/eval/*.{csv,json,geojson}   │
                         │   (reference blocks, sampling design, │
                         │    audit results — read-only data)    │
                         └───────────────┬────────────┘
                                          │  load() / _load_audit() / _load_json()
                                          ▼
                         ┌────────────────────────────┐
                         │        src/geoagent/tools.py         │
                         │  9 tools in the TOOLS dict:           │
                         │  list_places, change_summary,         │
                         │  block_evidence, uncertainty,         │
                         │  compare_places, query_blocks,        │
                         │  blocks_near, area_estimate,          │
                         │  audit_status                         │
                         └───┬───────────┬────────────┬─────────┘
                             │           │            │
                 ┌───────────┘           │            └───────────┐
                 ▼                       ▼                        ▼
   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐
   │   mcp_server.py       │  │   tool_cli.py         │  │   qgis_agent_panel.py     │
   │  JSON-RPC 2.0 /        │  │  no-LLM CLI            │  │  QGIS dock panel          │
   │  Model Context         │  │  (`list`,              │  │  (needs qgis.* — not      │
   │  Protocol server;      │  │   `<tool> "<args>"`)   │  │   installable via pip)    │
   │  used by MCP            │  │                        │  │  via panel_logic.py +     │
   │  Desktop et al.        │  │                        │  │  free_text_query.py       │
   └──────────┬─────────────┘  └──────────┬─────────────┘  └───────────┬─────────────┘
              │                           │                            │
              └─────────────┬─────────────┴────────────────────────────┘
                             ▼
                  ┌────────────────────────┐
                  │   tool_audit_log.py      │
                  │  optional, append-only    │
                  │  JSONL log of every call  │
                  │  (GEOAGENT_AUDIT_LOG)     │
                  └────────────────────────┘
```

## Layers

- **Data (`outputs/eval/`).** Small, already-finalized CSV/JSON/GeoJSON files: block geometry and labels
  (`eval_reference.geojson`), the sampling design (`eval_design.csv`), change-type and conformal-deferral
  detail, and the completed human audit's own result files. Nothing in this repository writes to this
  directory at runtime — every tool call is read-only.
- **Tool layer (`tools.py`).** The single source of truth: a `TOOLS` dict mapping each tool name to its
  function, description, and JSON-schema arguments. Both `mcp_server.py`'s `tools/list` and
  `tool_cli.py list` iterate this dict dynamically, so adding a tool here automatically exposes it
  everywhere with no changes needed elsewhere. `load()` caches the parsed data files in memory after the
  first call; `_load_audit()`/`_load_certainty_units()`/`_load_json()` are guarded passthroughs for the
  audit result files (empty/`{}` if a file is absent, never an error).
- **Extensions (`human_ref_tools.py`, `osm_hist_tools.py`, `osm_tools_v25.py`, `restricted_data.py`).** Importing
  these modules registers 19 further read-only tools in the same `TOOLS` dict: 11 over the 300-block human
  reference set and 8 over historical OpenStreetMap features. Their tables are not redistributed;
  `restricted_data.guard` turns a missing file into a structured, bilingual answer
  (see [data-availability.md](data-availability.md)).
- **Interfaces.** Three independent ways to call the same tools: `mcp_server.py` (JSON-RPC 2.0 over
  stdio, for MCP clients such as desktop assistants), `tool_cli.py` (a plain command-line entry point, no LLM or
  MCP client required — used throughout this repo's own docs and tests), and `qgis_agent_panel.py` (a QGIS
  dock widget, for use inside QGIS itself; requires QGIS's own Python and is not testable standalone).
- **Free-text parsing (`free_text_query.py`, `panel_logic.py`).** Bilingual (Arabic/English) query parsing
  and response formatting shared by the QGIS panel and its own test suite — pure logic, no data-file
  dependencies of its own.
- **Error recovery (`agent_recovery.py`).** Suggests corrections for near-miss place names or filter
  values (e.g. "Hazmia" → suggests "Hazmieh") rather than returning a silent empty result.
- **Audit log (`tool_audit_log.py`).** An optional, append-only JSONL log of every tool call (arguments,
  result summary, timestamp), enabled by setting `GEOAGENT_AUDIT_LOG` to a path; disabled by setting it to
  an empty string (used by the test suite so running tests never writes to `outputs/` as a side effect).

## Read-only design

No function in `tools.py`, `mcp_server.py`, `tool_cli.py`, or `qgis_agent_panel.py` opens any data file in
this repository in write mode. The only file this codebase ever writes is the optional audit log
(`outputs/agent_tool_audit_log.jsonl`), and that log records calls — it never feeds back into the tools'
own answers. This is intentional and tested: the agent can explain and cite the reference and audit data,
but cannot create, adjudicate, or modify a label or a result.

## Tests

Five independent suites (62 tests total) exercise every layer: `tests/test_tools.py` (the tool layer
itself, including a full MCP JSON-RPC round-trip via a real `mcp_server.py` subprocess),
`tests/test_agent_recovery.py`, `tests/test_panel_logic.py` (including the QGIS panel's pure logic without
requiring QGIS), `tests/test_tool_audit_log.py`, and `tests/test_free_text_query.py`. See the root
[README.md](../README.md#quick-start) for how to run them.
