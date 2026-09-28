# Results

This directory is a placeholder. The results this software's tools *report* live in
[`data/`](../data/README.md) (`outputs/eval/`) — small, finalized CSV/JSON/GeoJSON files the tool layer
reads directly. This `results/` directory documents what is intentionally **excluded** from this lean,
software-focused repository and remains in the full thesis submission bundle instead.

## Excluded from this repository

- **The full evaluation-run corpus** (`evaluation_runs/` in the main project) — intermediate outputs from
  every experimental run across the thesis's many analysis rounds (active-learning simulations, encoder
  and band-scale ablations, robustness checks, etc.). These are large, numerous, and not needed to run or
  test the live agent — only the handful of *final* result files listed in
  [../data/README.md](../data/README.md) are.
- **The benchmark corpora** (`benchmark/` in the main project) — the versioned question/answer benchmark
  sets (v2–v5) used to evaluate the agent's own free-text query understanding during development. Useful
  for the thesis's own evaluation chapter, not for running the shipped tool layer.
- **Any imagery-derived products** — hi-res chips, rasters, swipe-compare products, heatmaps, and other
  figures generated from satellite imagery during the thesis's GIS work. See
  [../docs/gis-workflow.md](../docs/gis-workflow.md) and [../data/README.md](../data/README.md) for why
  imagery itself is never included here.
- **Figures and generated plots** (`make_fig*.py` outputs) — thesis-chapter figures, not something the live
  agent needs at runtime.
- **The executive defense map set** (`outputs/maps/*.pdf`, `*.png` from `make_maps.py`) — 5 static
  cartographic PDFs/PNGs for a defense or review; `map_catalog()` in this repo's tool layer reports their
  local path and checks `exists` at call time, but the files themselves stay in the full thesis/GIS bundle.

## Where to find them

All of the above are part of the full GeoAgent-Lebanon thesis submission bundle prepared separately from
this repository. This repository's scope is deliberately narrower: the live, testable AI-agent / MCP tool
layer and the minimal data it needs to answer questions correctly — see the root
[README.md](../README.md) for what that includes.
