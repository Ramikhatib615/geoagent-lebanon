# Data

This repository ships only the small, derived reference and audit files the tool layer needs to run —
nothing in `outputs/eval/` is raw or high-resolution satellite imagery, and none of it is restricted.

## What is included (`outputs/eval/`)

| File | Size | What it is |
|---|---|---|
| `eval_reference.geojson` | ~125 KB | Geometry and attributes for all 200 stratified reference blocks (labels, annotators, place names, change type). |
| `eval_design.csv` | ~15 KB | The sampling design: stratum and weight for each block, used for design-weighted estimates. |
| `change_types_consensus.csv` | ~3.5 KB | Per-block agreed change-type classification. |
| `change_types/ct_index.json` | <1 KB | Path index mapping block ids to change-type crop image filenames — **the crop images themselves are not included** (see below). |
| `conformal_results_AI_consensus.json` | ~1 KB | Model-level conformal deferral rate used by `uncertainty()`. |
| `eval_results_AI_consensus.json` | ~4 KB | Pre-audit AI-consensus prevalence estimates, used by `area_estimate()` and cross-checked in tests. |
| `human_audit_results.csv` | ~25 KB | The completed blind two-reviewer human audit: both reviewers' labels, the final label, and the interpretation-sensitive flag, for the 80-block sample. |
| `human_audit_key_R26.csv` | ~4 KB | The pre-registered audit design, including which 13 blocks are Rule 1 "certainty units". |
| `appendix_g_rules23_R38.json` | <1 KB | The correlated-error test (Rule 2) result. |
| `audited_primary_reanalysis_R38.json` | ~2.5 KB | The audit-corrected headline AUC comparison and changed-area re-estimate. |

Total: well under 200 KB. All of these are the small, already-finalized *results* of the thesis's GIS and
audit workflow — not the workflow's inputs.

## What is NOT included

- **No raw or high-resolution satellite imagery** (Sentinel-2 scenes, Esri World Imagery/Wayback tiles, or
  any derived rasters). These are used in the thesis's GIS workflow (see
  [../docs/gis-workflow.md](../docs/gis-workflow.md)) under licenses that do not permit redistribution.
- **No change-type crop images** (`change_types/ct_*.png`) — only the path index that references them.
  These are small image crops for human interpretation, excluded here to keep the repository lean and
  imagery-free; `change_types/ct_index.json`'s paths simply won't resolve to a file in this repo.
- **No ArcGIS Pro project files, map packages, or QGIS project files.**
- **No full evaluation-run or benchmark corpora** — see [../results/README.md](../results/README.md).

If you need any of the above, they are part of the full thesis submission bundle, not this repository.
