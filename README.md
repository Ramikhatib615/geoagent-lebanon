# GeoAgent-Lebanon

![python](https://img.shields.io/badge/python-3.9%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

**A read-only, bilingual (Arabic–English) evidence agent for land-change screening in Lebanon.**

GeoAgent-Lebanon exposes the evidence behind a Sentinel-2 land-change screening study as 30 read-only tools
over the [Model Context Protocol](https://modelcontextprotocol.io) (MCP). A language-model assistant connected
to the server answers questions in Arabic or English by calling the tools; every answer is read from saved
result files and carries its caveats. The agent cannot create, change or delete a label.

This repository is the software companion to the Master's Project *GeoAgent-Lebanon: Uncertainty-Aware,
Label-Efficient Land-Change Screening and Prioritisation from Sentinel-2 Composites, with a Bilingual
(Arabic–English) Evidence Agent* (MSc Data Science, Lebanese American University).

## What it does

| Tool family | Tools | Evidence it reads | Data in this repository |
|---|---:|---|---|
| AI-consensus reference and audit | 11 | 200 stratified 420 m blocks (Beirut, Mount Lebanon), two AI annotation passes, a two-reviewer audit of 80 blocks | Included |
| Human reference | 11 | 300 blocks labelled by two human reviewers with an adjudicator (kappa 0.65) | Not redistributed (see [data availability](docs/data-availability.md)) |
| Historical OpenStreetMap | 8 | Mapped building footprints in 2018, 2022 and 2025 for the 300 blocks | Not redistributed |

When a restricted file is absent, its tools stay listed and return a structured, bilingual "dataset not
available" answer instead of failing. The test suite exercises them on synthetic fixtures.

## Design principles

- **Read-only.** No tool writes anything; a test asserts that no write tool exists.
- **Evidence, not generation.** Tools look up saved results. They do not run a model or reprocess imagery.
- **Caveats travel with the answer.** Every response states its scope: a sample is not full coverage, an
  AI-consensus label is not human ground truth, a mapped footprint is not a physical building.
- **Bilingual by design.** Place names, filter values and messages work natively in Arabic and English, with
  Arabic spelling and diacritic normalisation.
- **Auditable.** Every call through the server or the command line can be logged to an append-only JSONL file.
- **No dependencies.** The server, the command line and the tests use only the Python standard library.

## Quick start

```bash
git clone https://github.com/Ramikhatib615/geoagent-lebanon.git
cd geoagent-lebanon

# list the 30 tools and their schemas (no language model needed)
python src/geoagent/tool_cli.py list

# call a tool
python src/geoagent/tool_cli.py audit_status "{}"
python src/geoagent/tool_cli.py block_evidence "{\"block_id\": \"E137\"}"
python src/geoagent/tool_cli.py change_summary "{\"place\": \"الضاحية\"}"

# run the tests (six suites, 69 tests)
for t in tests/test_*.py; do python "$t"; done
```

Python 3.9 or later. No installation step is required.

## MCP client setup

Register the server in any MCP client that supports stdio servers:

```json
{
  "mcpServers": {
    "geoagent-lebanon": {
      "command": "python",
      "args": ["/absolute/path/to/geoagent-lebanon/src/geoagent/mcp_server.py"]
    }
  }
}
```

A ready-to-copy file is in [examples/mcp_client_config.json](examples/mcp_client_config.json). Restart the
client after changing the entry: a running server process keeps the tool list it started with. The server
implements `initialize`, `ping`, `tools/list` and `tools/call` (protocol 2024-11-05; compatible with later
clients).

## Example questions

| Question | Tool |
|---|---|
| How much changed area was estimated after the audit? | `audit_status` |
| What happened to blocks E137 and E199? | `block_evidence` |
| قديش المساحة المتغيّرة بعد التدقيق البشري؟ | `audit_status` |
| وين لازم يروح الإنسان يراجع؟ | `uncertainty` |
| Which reviewed blocks lie within 5 km of this point? | `human_blocks_near` |
| Is a block with no mapped footprint building-free? | `osm_building_free_status` |
| Can the data support a damage claim for this place? | `damage_claim_check` |

More in [examples/sample_queries.md](examples/sample_queries.md) and
[examples/sample_outputs.md](examples/sample_outputs.md). The full tool reference is in
[docs/mcp-tools.md](docs/mcp-tools.md).

## Key audited results the agent reports

- **Audit of the AI labels.** A two-reviewer audit of 80 blocks, conducted under a protocol that specified
  blinding, decided 75 blocks; the reviewers agreed on all 75, and 5 remain interpretation-sensitive.
- **Shared AI bias.** Where the two AI passes agreed, the audit disagreed on 17.7% of blocks, against about
  3% expected if their errors were independent.
- **Changed area.** 56.6 km² (95% interval 29.7 to 87.9) after audit correction, down from 82.1 km².
- **Model ranking.** The spectral score's lead over the random forest on the audited blocks is 0.13 AUC
  points with an interval spanning zero: reported as audit-sensitive, not as a confirmed result.

These are development results on a sample. See [Limitations](#limitations).

## Repository layout

```
src/geoagent/      tool layer, MCP server, command line, audit log, QGIS panel logic
tests/             six test suites and synthetic fixtures
outputs/eval/      small derived reference and audit files used by the 11 AI-consensus tools
docs/              architecture, tool reference, audit methodology, data availability, GIS workflow
examples/          sample queries, recorded outputs, MCP client configuration
```

## Limitations

- The 200-block reference set is a stratified sample of two areas, not full coverage of any place.
- AI-consensus labels are candidate reference labels. Only the 80 audited blocks carry a human label, and
  whether the reviewers could see the AI labels was not recorded at the time.
- The 300 human-reviewed blocks are reference labels at moderate agreement, not ground truth; reviewer
  names, dates and blinding are only partly documented.
- OpenStreetMap snapshots record what was mapped, not what existed. No building change is verified.
- Every reported model figure is development evidence. No independent Lebanese test has been run.
- The agent tests were written by the system's author and do not rank language models.
- No satellite imagery is distributed here (see [data/README.md](data/README.md)).

## Citation

If you use this software, please cite it using [CITATION.cff](CITATION.cff):

> El Khatib, R. (2026). *GeoAgent-Lebanon: a bilingual, read-only evidence agent for land-change screening in
> Lebanon* (version 0.5.0). Master's Project, MSc Data Science, Lebanese American University.

## Licence and data credits

Code: [MIT](LICENSE). Contains modified Copernicus Sentinel data (2018, 2025) in derived form only.
Administrative boundaries: OCHA COD-AB Lebanon via HDX (CC BY-IGO). OpenStreetMap-derived statistics:
© OpenStreetMap contributors (ODbL). Esri World Imagery was used only as a viewing aid during review and is
not redistributed.
