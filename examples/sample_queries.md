# Sample queries

Copy any of these into an MCP client (once the MCP server is configured — see
[../README.md](../README.md#mcp-client-setup)) or run them directly with no LLM via
`python src/geoagent/tool_cli.py <tool> "<json-args>"`. Recorded outputs for a subset of these are in
[sample_outputs.md](sample_outputs.md).

## English

- How much changed area was estimated after the audit?
- What happened to E137 and E199?
- Why is the spectral vs. random forest claim audit-sensitive?
- Which blocks still require human review?
- Which blocks were contested in the human audit?
- Compare spectral, random forest and DINOv2.
- Compare Dahieh and Hazmieh.
- What places have reference blocks in Mount Lebanon?
- How much of Dahieh changed between 2018 and 2025?
- Explain the difference between AI-consensus labels and human audit labels.

## Arabic (العربية)

- قديش المساحة المتغيّرة بعد التدقيق البشري؟
- شو صار بـ E137 و E199؟
- وين لازم يروح الإنسان يراجع؟
- قديش تغيّرت الضاحية؟
- شو الفرق بين تصنيف إجماع الذكاء الاصطناعي والتصنيف بعد التدقيق البشري؟

## Direct CLI equivalents

```bash
python src/geoagent/tool_cli.py audit_status "{}"
python src/geoagent/tool_cli.py audit_status "{\"lang\": \"ar\"}"
python src/geoagent/tool_cli.py block_evidence "{\"block_id\": \"E137\"}"
python src/geoagent/tool_cli.py block_evidence "{\"block_id\": \"E199\"}"
python src/geoagent/tool_cli.py query_blocks "{\"annotators_disagree\": true}"
python src/geoagent/tool_cli.py compare_places "{\"place_a\": \"Dahieh\", \"place_b\": \"Hazmieh\"}"
python src/geoagent/tool_cli.py list_places "{\"governorate\": \"Mount Lebanon\"}"
python src/geoagent/tool_cli.py change_summary "{\"place\": \"الضاحية\"}"
```
