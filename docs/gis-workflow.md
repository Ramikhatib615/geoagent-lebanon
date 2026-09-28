# GIS workflow (ArcGIS Pro side)

This repository ships the AI-agent / MCP tool layer only. The GIS work that produced and interpreted the
underlying reference and audit data lives in the full thesis submission bundle (ArcGIS Pro project files,
map packages, and high-resolution imagery), not here. This document explains how that GIS work relates to
the data this repo does include, so a reader of the code understands where the numbers ultimately come
from.

## What ArcGIS Pro was used for

- **Evidence book / change atlas:** per-block map layouts pairing the 2018 and 2025 Sentinel-2 composites
  side by side for each of the 200 reference blocks, used by the AI annotation and adjudication process
  and by human reviewers during the audit.
- **Operational review map:** a single map showing all 200 blocks styled by label, stratum, and AOI, used
  to sanity-check the spatial distribution of the stratified sample across Beirut and Mount Lebanon before
  and after the audit.
- **Audit maps:** map layouts specific to the 80-block audit sample, styled to distinguish the 13 Rule 1
  certainty units, the 5 interpretation-sensitive blocks, and the blocks whose label flipped, for the human
  reviewers to work from during the blind review.
- **High-resolution imagery as an interpretation aid only:** Esri World Imagery (including Wayback
  historical imagery) was used to help human reviewers interpret ambiguous blocks during the audit — it
  was never used to generate or override an AI-consensus label programmatically, and it is not
  redistributed in this repository (see [data/README.md](../data/README.md)).

## Map package and outputs

The ArcGIS Pro project (`.aprx`), its map packages, and rendered map exports are part of the full thesis
submission bundle, not this repository. What this repository's `outputs/eval/` directory contains instead
are the **small, derived, already-finalized results** of that GIS/audit work — block geometry
(`eval_reference.geojson`), the sampling design (`eval_design.csv`), change-type crop index
(`change_types/ct_index.json`, paths only — the crop images themselves are not shipped), and the audit's
own result files. The tool layer reads these files as a read-only passthrough; it does not open, query, or
depend on ArcGIS Pro or any GIS software at runtime.

## `qgis_agent_panel.py`

The one file in `src/geoagent/` that *does* depend on a GIS application is `qgis_agent_panel.py` — a QGIS
plugin dock panel that lets a user ask the same questions this repo's MCP tools answer, from inside QGIS
itself, using the same underlying `tools.py`/`panel_logic.py`/`free_text_query.py` logic. It imports
`qgis.core`, `qgis.utils`, and `qgis.PyQt`, which only exist inside QGIS's own bundled Python — it cannot
be installed via `pip` and is not part of the MCP server, CLI, or test suite covered elsewhere in this
repository. Its pure logic (parsing, formatting, choice-population) is exercised without QGIS by
`panel_logic.py` and `tests/test_panel_logic.py`.

## Restricted imagery is not redistributed here

Sentinel-2 composites and Esri World Imagery / Wayback tiles are used throughout the thesis's GIS workflow
under their respective providers' licenses, which do not permit redistribution. This repository contains
no raw or high-resolution imagery, no imagery tiles or caches, and no ArcGIS project files — only the
small, derived CSV/JSON/GeoJSON result files listed in [data/README.md](../data/README.md). See
`.gitignore` for the patterns that keep any of this out of version control even if it is present locally.
