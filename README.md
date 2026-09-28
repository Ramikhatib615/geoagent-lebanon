# GeoAgent-Lebanon — Auditable AI Agent for Satellite Change Analysis

**Data Science + GIS + AI agent project.** A read-only, tool-using AI agent (Arabic and English) that
answers questions about 2018→2025 land-cover change in Beirut and Mount Lebanon, grounded entirely in
a stratified reference sample, a completed human audit, and a set of defense-ready static maps — never in free generation, and never by
editing the underlying labels or files.

> This repository is the software-packaging companion to a master's thesis (GeoAgent-Lebanon:
> Label-Efficient, Uncertainty-Aware Change Monitoring with Foundation-Model Embeddings and LLM Agents).
> It ships only the live tool layer, its tests, and the small reference/audit data files the tools need
> to run — not the full thesis submission bundle, its GIS project files, or any satellite imagery.

## What this is (and isn't)

- **Change evidence, not a live detector.** Every answer is read from a pre-computed, stratified
  sample of 200 reference blocks (420 m, Beirut + Mount Lebanon) already labelled by two independent
  AI annotators plus adjudication — comparing Sentinel-2 composites from 2018 and 2025. The agent does
  not run a model or reprocess imagery when you ask it a question; it looks up and explains existing results.
- **AI-consensus labels are candidate reference labels, not human ground truth.** They come from two AI
  annotators agreeing (or a third AI adjudicator breaking a tie) — never from a person looking at the
  block, unless it went through the audit below.
- **A blind, two-reviewer human audit has been completed on the 80 blocks the thesis's own sensitivity
  analysis flagged as decision-sensitive** (not all 200). 75 of the 80 were decided; 5 remain genuinely
  interpretation-sensitive between the two human reviewers themselves. The audited numbers below are the
  ones this repository's tools report as primary wherever the two differ.

## Key features

- **11 read-only MCP tools** (`list_places`, `change_summary`, `block_evidence`, `uncertainty`,
  `compare_places`, `query_blocks`, `blocks_near`, `area_estimate`, `audit_status`, `map_catalog`,
  `block_demo`) exposed over the Model Context Protocol, so any MCP-capable assistant (e.g. Claude
  Desktop) can query them directly — see [docs/mcp-tools.md](docs/mcp-tools.md) for the full reference.
- **Bilingual by design**, not by translation: place names, filter values (`تغيّر`/`change`,
  `جبل لبنان`/`Mount Lebanon`, …), and every response message work natively in Arabic and English, with
  Arabic diacritic/spelling normalisation so `الضاحية` and `الضَّاحية` resolve to the same blocks.
- **Audit-aware.** `audit_status()` and `block_evidence()`'s `human_audit` field surface the completed
  audit's outcome directly: which blocks flipped, the correlated-error test result, and the resulting
  audited AUC comparison and changed-area estimate — not just the raw, pre-audit numbers.
- **A command-line interface** (`tool_cli.py`) that exercises every tool with no LLM and no MCP client
  needed — useful for demos, debugging, and CI.
- **Every call logged.** An optional, append-only JSONL audit log (`tool_audit_log.py`) records every
  tool call made through the CLI, the MCP server, or the QGIS panel, for later review.
- **Fully tested.** 5 independent test suites (63 tests total) cover the tool layer, the MCP protocol
  round-trip, free-text query parsing, the QGIS panel's pure logic, error recovery/suggestions, and the
  audit log — see [Quick start](#quick-start) to run them yourself.

## What the agent can and cannot do

**Can:** answer bilingual questions grounded in the reference sample and the completed audit; cite the
specific block id(s), counts, and files behind any answer; state a caveat whenever an answer covers a
sample rather than full coverage, or an AI-consensus rather than an audited label; refuse or hedge on
questions it cannot answer from the data it has; distinguish AI-level uncertainty (`uncertainty()`,
annotator disagreement / conformal deferral) from the human audit's own `interpretation_sensitive` flag
— these are different signals and can disagree (e.g. block E056: the two AI annotators agreed easily,
but the two human reviewers did not).

**Cannot:** create, adjudicate, or overwrite a label in the reference layer or the audit results; run a
change-detection model or reprocess new imagery; claim human ground truth for any of the 120 blocks
outside the 80-block audit sample, or for the 5 still-undecided blocks inside it; access anything outside
its own read-only data files.

## Quick start

```bash
git clone <this-repo-url> geoagent-lebanon
cd geoagent-lebanon

# Run the full test suite (63 tests across 5 files; GEOAGENT_AUDIT_LOG="" keeps tests
# from writing to outputs/ as a side effect)
GEOAGENT_AUDIT_LOG="" python tests/test_tools.py
GEOAGENT_AUDIT_LOG="" python tests/test_agent_recovery.py
GEOAGENT_AUDIT_LOG="" python tests/test_panel_logic.py
GEOAGENT_AUDIT_LOG="" python tests/test_tool_audit_log.py
GEOAGENT_AUDIT_LOG="" python tests/test_free_text_query.py

# No LLM needed -- list every tool's schema
python src/geoagent/tool_cli.py list

# Ask a question directly via the CLI
python src/geoagent/tool_cli.py audit_status "{}"
python src/geoagent/tool_cli.py block_evidence "{\"block_id\": \"E137\"}"
```

Requires Python 3.9+ and nothing else (see [requirements.txt](requirements.txt) — the tool layer is
pure standard library).

## Visual demo

Beyond the 9 data tools above, two more read-only tools make the agent map-aware for a defense or review
by someone who has not lived inside this project: `map_catalog()` lists the 5 static "executive defense
map" PDFs/PNGs (title, thesis section, talking point, caveat, local path), and `block_demo(block_id)`
gives a single-block defense card (AI-consensus label, human-audit outcome, why it matters, which map(s)
show it, a plain-language explanation) — built for blocks like `E137`/`E199` (the two decisive Rule 1
flips) and the 5 still-contested blocks (`E056`, `E080`, `E120`, `E123`, `E180`).

**The map PDFs/PNGs themselves are not in this GitHub repository** — like the raw imagery and ArcGIS Pro
project (see [data/README.md](data/README.md)), they live in the full local thesis/GIS bundle.
`map_catalog()` reports each map's local path and checks `exists` fresh on every call; it never claims a
file is present that it cannot see. This repo ships the agent and the small data the maps and tools are
both built from, so `map_catalog()`/`block_demo()` run and test cleanly here even without the map files
present — only the `exists` flags and the images themselves need the full bundle.

See [docs/visual-demo.md](docs/visual-demo.md) for the executive map set, the styling convention, and the
recommended defense flow, and [examples/visual_demo_script.md](examples/visual_demo_script.md) for a
ready-to-run 5-minute script.

## Claude Desktop MCP setup

Add this to Claude Desktop's config (Settings → Developer → Edit Config, under `mcpServers`), replacing
the path with wherever you cloned this repo:

```json
{
  "mcpServers": {
    "geoagent-lebanon": {
      "command": "python",
      "args": ["C:/path/to/geoagent-lebanon/src/geoagent/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop after adding or changing this entry so it picks up the current 11-tool list. See
[examples/claude_desktop_config.json](examples/claude_desktop_config.json) for a ready-to-copy file and
[docs/mcp-tools.md](docs/mcp-tools.md) for what each tool does.

## CLI usage

```bash
python src/geoagent/tool_cli.py list                                        # schema of all 11 tools
python src/geoagent/tool_cli.py change_summary "{\"place\": \"Dahieh\"}"
python src/geoagent/tool_cli.py area_estimate "{\"aoi\": \"beirut\"}"
python src/geoagent/tool_audit_log.py outputs/agent_tool_audit_log.jsonl    # summarise the call log
```

## Example questions (Arabic and English)

| # | Question | Tool(s) |
|---|---|---|
| 1 | How much changed area was estimated after the audit? | `audit_status` |
| 2 | What happened to E137 and E199? | `block_evidence` |
| 3 | Why is the spectral-vs-random-forest claim audit-sensitive? | `audit_status` |
| 4 | قديش المساحة المتغيّرة بعد التدقيق البشري؟ | `audit_status` (lang=ar) |
| 5 | شو صار بـ E137 و E199؟ | `block_evidence`, `audit_status` (ar) |
| 6 | وين لازم يروح الإنسان يراجع؟ | `audit_status` (`interpretation_sensitive_blocks`) |
| 7 | Which blocks were contested in the human audit? | `audit_status` |
| 8 | Compare spectral, random forest and DINOv2. | `audit_status` (`audited_headline_auc`) |

More in [examples/sample_queries.md](examples/sample_queries.md); recorded answers to all of the above in
[examples/sample_outputs.md](examples/sample_outputs.md) and [docs/demo-questions.md](docs/demo-questions.md).

## Audit-aware examples (live output, `audit_status()`)

- **Changed area after the audit:** 56.6 km² (95% CI 29.7–87.9), down from the uncorrected 82.1 km²
  (Beirut 3.9 km², Mount Lebanon 52.7 km²).
- **E137 and E199:** both were AI-consensus `change` (agreed by both AI annotators); both reviewers
  audited both blocks to `no_change`. These are 2 of the 13 pre-registered "certainty units" (Rule 1),
  and this pair flipping is what makes the spectral-vs-random-forest ranking `not_supported_audit_sensitive`
  rather than a confirmed result.
- **Reviewer agreement:** 75/75 decided blocks (100%) — the two reviewers agreed on every block they were
  able to decide; 5 blocks (E056, E080, E120, E123, E180) remain genuinely interpretation-sensitive between
  them and are reported as undecided, not resolved by majority or tie-break.
- **Contested / flagged for follow-up:** the 5 interpretation-sensitive blocks above (human-audit
  disagreement) are a different set from the 38 blocks where the two *AI* annotators originally disagreed
  (`query_blocks(annotators_disagree=true)`) — see [docs/audit-methodology.md](docs/audit-methodology.md)
  for how the two are related and why they aren't the same list.

## Limitations

- The 200-block reference set is a **stratified sample** of two AOIs, not full coverage of any town,
  city, or governorate — `list_places`/`change_summary` answers must not be read as covering an entire
  place.
- AI-consensus labels are **not human ground truth**; only the 80 audited blocks have a human-reviewed
  label, and of those, 5 remain undecided even after the audit.
- The agent is **read-only end to end**: no tool can create, adjudicate, or modify a label, a file, or the
  audit results, in either this repo or the thesis's own result files.
- `uncertainty()` reports an **AI-level** deferral signal (annotator disagreement / conformal coverage),
  which is not the same thing as the human audit's own `interpretation_sensitive` flag — see
  [docs/audit-methodology.md](docs/audit-methodology.md).
- This repository does not include restricted or high-resolution imagery (see
  [data/README.md](data/README.md)) and is not a substitute for the full thesis submission bundle, which
  additionally contains the ArcGIS Pro project, the full evaluation/benchmark corpora, and the thesis
  document itself.

## Data and licensing

- **Code:** MIT License — see [LICENSE](LICENSE).
- **Reference and audit data** (`outputs/eval/`): small, derived CSV/JSON/GeoJSON files (block geometry,
  labels, and audit results) produced by the thesis's own evaluation and audit pipeline. See
  [data/README.md](data/README.md) for exactly what is and isn't included, and
  [results/README.md](results/README.md) for what is excluded from this lean repo (the larger evaluation
  run corpus, benchmark sets, and any imagery-derived products) and stays in the full thesis bundle.
- **Imagery:** Sentinel-2 composites and Esri World Imagery (including Wayback) are used for interpretation
  and figure-making in the thesis and are **not redistributed** here under their respective licenses; see
  [docs/gis-workflow.md](docs/gis-workflow.md).

## Citation / thesis reference

If you use or refer to this tool layer, please cite the underlying thesis:

> Khatib, R. (2026). *GeoAgent-Lebanon: Label-Efficient, Uncertainty-Aware Change Monitoring with
> Foundation-Model Embeddings and LLM Agents (Arabic–English).* Master's thesis.

This repository packages the thesis's live AI-agent / MCP tool layer for reproducible use and review; it
does not itself present new scientific results beyond what the thesis reports (Section 5.14 / Appendix G
for the audit, Chapters 4–5 for the primary analysis).

## Documentation

- [docs/architecture.md](docs/architecture.md) — how the pieces fit together
- [docs/mcp-tools.md](docs/mcp-tools.md) — all 9 tools, inputs, outputs, caveats, example questions
- [docs/audit-methodology.md](docs/audit-methodology.md) — the human audit protocol and Rule 1 / Rule 2
- [docs/gis-workflow.md](docs/gis-workflow.md) — the ArcGIS Pro side of the project
- [docs/demo-questions.md](docs/demo-questions.md) — a ready-to-run text-question demo script
- [docs/visual-demo.md](docs/visual-demo.md) — the executive map set and the visual defense flow
