# Data availability

| Dataset | Used by | In this repository | Reason |
|---|---|---|---|
| 200-block AI-consensus reference, sampling design, change types, conformal summary (`outputs/eval/`) | 11 AI-consensus and audit tools | Yes | Small derived tables produced by the project |
| 80-block audit results and key (`outputs/eval/human_audit_*.csv`) | `audit_status`, `block_evidence`, `block_demo` | Yes, with reviewers identified by role only | Reviewer identities are not published |
| 300-block human reference set (`data/human_ref/human_ref_300.csv`) | 11 human-reference tools | No | The labels were made on third-party imagery whose terms for redistribution of derived labels are not confirmed, and the table carries per-block model scores |
| Block-level historical OpenStreetMap features (`data/osm_hist/block_osm_features_300.csv`) | 8 OSM tools | No | The table is joined to the human labels and scores above |
| Sentinel-2 composites, Esri World Imagery views, map exports | none of the tools | No | Imagery is not redistributed |

## Behaviour without the restricted files

The 19 tools that need a restricted file remain registered. Called without the file, a tool returns:

```json
{"found": false, "available": false, "dataset": "300-block human reference set",
 "error": "The 300-block human reference set is not distributed with the public repository. ..."}
```

Tools that state a rule and need no file (`osm_mapping_vs_physical`, `osm_physical_verification`,
`damage_claim_check` for a place) answer normally.

## Using your own copy

Place the files at the default paths above, or point the server to them:

```bash
export GEOAGENT_HUMAN_REF=/path/to/human_ref_300.csv
export GEOAGENT_OSM_HIST=/path/to/block_osm_features_300.csv
```

## Synthetic fixtures

`tests/fixtures/` holds two synthetic tables with the same columns, generated from a fixed seed by
`make_synthetic_fixtures.py`. Block identifiers lie outside the real grid, and no value describes a real
block, label, score or reviewer decision. They exist only so that the tests can run every tool.

Requests for the restricted tables for research use can be addressed to the author.
