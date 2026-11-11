# Sample outputs

Real, live outputs from `tool_cli.py` in this repo (not hand-edited), captured for the demo questions in
[../docs/demo-questions.md](../docs/demo-questions.md). Numbers here will always match `outputs/eval/`
because the tool layer never recomputes them — it only reads and reports.

## `audit_status()` — demo questions 1, 3, 6, 8

```
$ python src/geoagent/tool_cli.py audit_status "{}"
{
 "found": true,
 "n_audited": 80,
 "n_decided": 75,
 "n_interpretation_sensitive_undecided": 5,
 "interpretation_sensitive_blocks": [
  "E056",
  "E080",
  "E120",
  "E123",
  "E180"
 ],
 "reviewer_agreement_n": 75,
 "reviewer_agreement_rate": 1.0,
 "blocks_where_audited_label_differs_from_ai_consensus": [
  "E002",
  "E015",
  "E020",
  "E060",
  "E065",
  "E078",
  "E087",
  "E105",
  "E137",
  "E147",
  "E148",
  "E170",
  "E182",
  "E193",
  "E194",
  "E197",
  "E199"
 ],
 "rule1_certainty_units": {
  "n_units": 13,
  "block_ids": [
   "E033",
   "E037",
   "E040",
   "E068",
   "E077",
   "E094",
   "E098",
   "E103",
   "E107",
   "E117",
   "E137",
   "E168",
   "E199"
  ],
  "n_flipped": 2,
  "flipped_block_ids": [
   "E137",
   "E199"
  ],
  "meaning": "These 13 blocks were fixed before any review as the pre-registered test of the headline ranking (8 pivotal no-change blocks that must hold, 5 Mount Lebanon-low change blocks). A flip here is what makes the spectral-vs-random-forest ranking 'not supported', separately from the broader 'differs from AI-consensus' list above, which includes ordinary audit disagreements outside this set."
 },
 "correlated_error_test": {
  "fires": true,
  "ai_agreed_error_rate": 0.1774,
  "auditor_error_estimate": 0.0312,
  "gap_percentage_points": 14.62
 },
 "audited_headline_auc": {
  "spectral": 0.6159,
  "random_forest": 0.4842,
  "dinov2": 0.4823,
  "gap_spectral_minus_rf": 0.1317,
  "gap_95ci": [
   -0.0743,
   0.3377
  ],
  "conclusion": "not_supported_audit_sensitive"
 },
 "audited_area_estimate_km2": {
  "corrected": 56.6,
  "corrected_95ci": [
   29.7,
   87.9
  ],
  "uncorrected": 82.1,
  "beirut_corrected": 3.9,
  "mount_lebanon_corrected": 52.7
 },
 "message": "The Appendix G two-reviewer human audit (protocol specified blinding) is complete: 75/80 blocks decided (5 left interpretation-sensitive, undecided); reviewers agreed on 75/75 final labels. 17 block(s) overall differ from their AI-consensus label: E002, E015, E020, E060, E065, E078, E087, E105, E137, E147, E148, E170, E182, E193, E194, E197, E199. Of the 13 pre-registered 'certainty units' (Rule 1: 8 pivotal no-change blocks plus 5 Mount Lebanon-low change blocks), 2 flipped: E137, E199 -- it is this Rule 1 flip, not the broader 17-block list, that drives the headline finding. The correlated-error test fired (Rule 2). The audited spectral-vs-random-forest AUC gap is 0.132, 95% CI [-0.074, 0.338] -- reported as not supported / audit-sensitive, not a confirmed win for either model. The audited, per-stratum-corrected changed area is 56.6 km^2 (95% CI [29.7, 87.9]), revised down from the uncorrected 82.1 km^2.",
 "note": "This audit covers only the 80-block decision-sensitive subset, not the full 200-block sample.",
 "caveats": [
  "Blocks are a stratified sample of 420 m blocks in two AOIs (Beirut, Mount Lebanon), not full coverage of any place.",
  "Labels are AI consensus (two independent AI annotators plus adjudication), not human ground truth, unless human_check is filled.",
  "The place name is the nearest named place to the block centre, not the administrative extent of that place.",
  "Change means visible change between Sentinel-2 composites of 2018 and 2025 at 10 m resolution; small changes can be missed."
 ]
}
```

## `block_evidence("E137")` — demo questions 2, 5

```
$ python src/geoagent/tool_cli.py block_evidence "{\"block_id\": \"E137\"}"
{
 "id": "E137",
 "aoi": "mount_lebanon",
 "stratum": "low",
 "weight": 29.0,
 "label": "change",
 "label_source": "agreed",
 "annotator_A": "change",
 "annotator_B": "change",
 "place_en": "Bteghrine",
 "place_ar": "بتغرين",
 "admin_en": "Marjaba",
 "admin_ar": "مرجبا",
 "governorate": "Mount Lebanon Governorate",
 "human_check": "",
 "centre_lon": 35.749034,
 "centre_lat": 33.920725,
 "bbox_lonlat": [
  35.746704,
  33.918782,
  35.751364,
  33.922667
 ],
 "screening_score": 0.05361,
 "change_type": "new_construction",
 "change_type_status": "agreed",
 "type_conf_A": "medium",
 "type_conf_B": "low",
 "type_sheet": "outputs/eval/change_types/ct_08.png",
 "found": true,
 "label_localised": "change",
 "change_type_localised": "new_construction",
 "aoi_localised": "mount_lebanon",
 "stratum_localised": "low",
 "label_status_localised": "agreed",
 "human_audit": {
  "audited": true,
  "human_1": "no_change",
  "human_2": "no_change",
  "human_final": "no_change",
  "interpretation_sensitive": false,
  "reviewer_1": "Reviewer 1",
  "reviewer_2": "Reviewer 2",
  "differs_from_ai_consensus_label": true,
  "note": "This block is part of the two-reviewer human audit (protocol specified blinding) (Appendix G). human_final is the audited label; it can differ from the AI-consensus 'label' field above -- when it does, the audited label is the one the project report treats as primary from Section 5.3.4 onward."
 },
 "caveats": [
  "Blocks are a stratified sample of 420 m blocks in two AOIs (Beirut, Mount Lebanon), not full coverage of any place.",
  "Labels are AI consensus (two independent AI annotators plus adjudication), not human ground truth, unless human_check is filled.",
  "The place name is the nearest named place to the block centre, not the administrative extent of that place.",
  "Change means visible change between Sentinel-2 composites of 2018 and 2025 at 10 m resolution; small changes can be missed."
 ]
}
```

E199 has the same shape (AI-consensus `change`, audited `human_final: "no_change"`,
`differs_from_ai_consensus_label: true`) — run `block_evidence "{\"block_id\": \"E199\"}"` to see it
directly.

## `change_summary("Dahieh")` — a non-audit example, for contrast

```
$ python src/geoagent/tool_cli.py change_summary "{\"place\": \"Dahieh\"}"
{
 "found": true,
 "query": "Dahieh",
 "match_type": "exact",
 "matched_places": [
  {
   "place_en": "Dahieh",
   "place_ar": "الضاحية الجنوبية"
  }
 ],
 "n_blocks": 20,
 "labels": {
  "change": 4,
  "no_change": 13,
  "uncertain": 3
 },
 "labels_localised": {
  "change": 4,
  "no_change": 13,
  "uncertain": 3
 },
 "change_types": {
  "demolition_damage": 3,
  "new_construction": 1
 },
 "share_changed_among_decided_blocks": 0.235,
 "block_ids": [
  "E003",
  "E023",
  "E032",
  "E039",
  "E045",
  "E065",
  "E067",
  "E076",
  "E089",
  "E090",
  "E093",
  "E100",
  "E112",
  "E129",
  "E144",
  "E148",
  "E175",
  "E177",
  "E179",
  "E187"
 ],
 "human_checked_blocks": [
  "E065",
  "E067",
  "E112",
  "E187"
 ],
 "message": "20 sampled block(s) matched 'Dahieh': 4 show change, 13 show no change, 3 are uncertain.",
 "interpretation_note": "The share is unweighted (blocks were sampled with unequal probabilities by stratum) and must not be generalised to the whole place.",
 "caveats": [
  "Blocks are a stratified sample of 420 m blocks in two AOIs (Beirut, Mount Lebanon), not full coverage of any place.",
  "Labels are AI consensus (two independent AI annotators plus adjudication), not human ground truth, unless human_check is filled.",
  "The place name is the nearest named place to the block centre, not the administrative extent of that place.",
  "Change means visible change between Sentinel-2 composites of 2018 and 2025 at 10 m resolution; small changes can be missed."
 ]
}
```

## `query_blocks(annotators_disagree=true)` — the *AI*-disagreement set, for contrast with the human audit

```
$ python src/geoagent/tool_cli.py query_blocks "{\"annotators_disagree\": true}"
{
 "n_blocks": 38,
 ...
}
```

38 blocks where the two AI annotators originally disagreed — a different, larger set than the 5
interpretation-sensitive blocks the two *human* reviewers disagreed on
(`audit_status().interpretation_sensitive_blocks`). See
[../docs/audit-methodology.md](../docs/audit-methodology.md) for why these are not the same list.
