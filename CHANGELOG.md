# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0] - 2026-11-11

### Added
- 11 read-only tools over the 300-block human reference set (`human_block_lookup`, `human_label_provenance`,
  `human_reviewer_agreement`, `human_unresolved`, `model_vs_human`, `human_regional_performance`,
  `building_footprint_evidence`, `damage_claim_check`, `human_query_blocks`, `human_blocks_near`,
  `human_dataset_scope`).
- 8 read-only historical OpenStreetMap tools (`osm_block_history`, `osm_mapping_vs_physical`,
  `osm_building_free_status`, `osm_vs_scores`, `osm_region_coverage`, `osm_contradictions`,
  `osm_physical_verification`, `osm_zero_footprint_summary`). The server now lists 30 tools.
- Graceful, bilingual "dataset not available" answers when a restricted file is absent
  (`restricted_data.py`), with `GEOAGENT_HUMAN_REF` and `GEOAGENT_OSM_HIST` overrides.
- `tests/test_extended_tools.py` and synthetic fixtures; `docs/data-availability.md`; `CITATION.cff`;
  `pyproject.toml`.

### Changed
- Documentation rewritten for the Master's Project report; section references follow the current report.
- The 80-block audit is described as a two-reviewer audit conducted under a protocol that specified blinding.
- Reviewers in `human_audit_results.csv` are identified by role only.
- The `map_catalog` section field is now named `report_section`.
- MCP client configuration example renamed to `examples/mcp_client_config.json`.

## [0.4.0] - 2026-09-28

### Added
- `map_catalog` and `block_demo`; 11 tools in total.

## [0.3.0] - 2026-09-28

### Added
- Initial public release: 9 read-only tools, MCP server, command line, audit log and tests.
