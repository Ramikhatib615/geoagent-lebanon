# Screenshots

This directory is a placeholder for demo screenshots to accompany the repository. None are included yet —
add them here (PNG or JPG, descriptive filenames) when available. Suggested set:

1. **`mcp-client-demo.png`** — an MCP client with the `geoagent-lebanon` MCP server connected, showing
   a live question and answer (e.g. "What happened to E137 and E199?" from
   [../docs/demo-questions.md](../docs/demo-questions.md)).
2. **`audit-status-output.png`** — the CLI or agent's response to `audit_status()`, showing the 75/80
   agreement figure and the audit-corrected 56.6 km² changed-area estimate.
3. **`block-evidence-e137-e199.png`** — the `block_evidence` response for E137 and/or E199, showing the
   `human_audit` field with the AI-consensus label flipped to the audited `no_change`.
4. **`arcgis-audit-interface.png`** — the ArcGIS Pro audit map layout used by the two human reviewers
   during the audit (see [../docs/gis-workflow.md](../docs/gis-workflow.md)).
5. **`operational-map.png`** — the operational review map showing all 200 reference blocks styled by
   label, stratum, and AOI across Beirut and Mount Lebanon.

Keep screenshots small (PNG, reasonably compressed) and free of any sensitive local file paths or personal
information from the machine they were taken on.
