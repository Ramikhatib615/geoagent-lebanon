# MCP tools reference

All 11 tools are exposed over the Model Context Protocol by `src/geoagent/mcp_server.py`, and directly as
Python functions / a CLI by `src/geoagent/tools.py` / `src/geoagent/tool_cli.py`. The `TOOLS` dict in
`tools.py` is the single source of truth: both the MCP server's `tools/list` and `tool_cli.py list`
iterate it dynamically, so this list is always exactly what a running server or the CLI will report.

Every tool accepts an optional `lang` argument (`auto` / `en` / `ar`, default `auto` — inferred from the
place name or block id supplied) and every response includes a `caveats` array (4 standing caveats about
sample coverage, AI-consensus vs. ground truth, place-name matching, and the definition of "change") in
the response language. These are omitted below for brevity — assume every tool has them.

---

## `list_places`

**Purpose:** list named places (Arabic or English) that have reference blocks, with per-place counts by
label.

**Inputs:** `query` (optional partial name, either language), `governorate` (optional), `limit`
(optional), `lang`.

**Output summary:** `places` (list of `{name_en, name_ar, n_blocks, labels: {change, no_change,
uncertain}}`), `n_unnamed_blocks`, `total_matching_places`.

**Caveats beyond the standard 4:** none additional.

**Example question:** "What places have reference blocks in Mount Lebanon?"

---

## `change_summary`

**Purpose:** summarise the reference-block evidence of 2018→2025 change for a place name or a single
block id — raw counts and change types, never extrapolated to the whole named place.

**Inputs:** `place` (required — place name or block id, Arabic or English), `lang`.

**Output summary:** `found`, `n_blocks`, `labels` (counts), `change_types` (counts), bilingual `message`;
on a not-found place, `suggestions` (pruned, plausible near-matches only).

**Caveats beyond the standard 4:** the response explicitly does not claim the named place's full extent
changed — only the sampled blocks near it.

**Example question:** "How much of Dahieh changed?" / "قديش تغيّرت الضاحية؟"

---

## `block_evidence`

**Purpose:** the full evidence record for one reference block (E001–E200): location, both AI annotators'
labels, adjudication, change type and confidence, and — for any of the 80 audited blocks — the completed
human audit outcome via the `human_audit` field.

**Inputs:** `block_id` (required, e.g. `E137`), `lang`.

**Output summary:** location (`place_en/ar`, `admin_en/ar`, `governorate`, `centre_lat/lon`, `bbox_lonlat`),
`label`, `label_source` (`agreed`/`adjudicated`), `annotator_A`/`annotator_B`, `change_type` and
confidences, `type_sheet` (path to the change-type crop image, not shipped in this repo), and
`human_audit`: `{audited, human_1, human_2, human_final, interpretation_sensitive, reviewer_1, reviewer_2,
differs_from_ai_consensus_label, note}` — `audited: false` with an explanatory note for any of the 120
blocks outside the audit sample.

**Caveats beyond the standard 4:** `human_audit.note` states explicitly whether this block's label is
AI-consensus only or has been through the blind human audit, and which one the thesis treats as primary
when they differ.

**Example question:** "What happened to E137 and E199?" / "شو صار بـ E137 و E199؟"

---

## `uncertainty`

**Purpose:** an **AI-level** deferral assessment — which blocks of a place (or a single block id) an AI
model itself would defer to a human reviewer, and why (label disagreement, adjudication, or conformal
non-coverage) — plus the model's overall conformal deferral rate. This is distinct from the human audit's
own `interpretation_sensitive` flag (see `audit_status` and
[docs/audit-methodology.md](audit-methodology.md)): e.g. block E056 has `defer_to_human: false` here (the
two AI annotators agreed easily) yet is one of the 5 blocks the two *human* reviewers could not agree on.

**Inputs:** `place` (required — place name or block id), `lang`.

**Output summary:** `blocks` (list of `{id, defer_to_human, reasons}`), model-level conformal deferral
rate.

**Caveats beyond the standard 4:** the response does not claim these are the same blocks flagged by the
human audit.

**Example question:** "Which blocks near Dahieh would the model defer to a human?"

---

## `compare_places`

**Purpose:** compare two places' change evidence side by side; explicitly refuses to produce a ranking
when either place has fewer than 5 sampled blocks.

**Inputs:** `place_a`, `place_b` (both required), `lang`.

**Output summary:** per-place `n_blocks`/`labels`, `ranking_allowed` (boolean), and the ranking itself only
when `ranking_allowed` is true.

**Caveats beyond the standard 4:** an explicit refusal message (not a guess) when the sample is too small
to compare.

**Example question:** "Compare spectral, random forest and DINOv2." (via `audit_status`'s
`audited_headline_auc` for the model comparison; `compare_places` is for comparing two named *places'*
change evidence, e.g. "Compare Dahieh and Hazmieh.")

---

## `query_blocks`

**Purpose:** count and list reference blocks matching any combination of filters — the general-purpose
lookup underneath the other tools.

**Inputs (all optional, combine with AND):** `aoi`, `governorate`, `label`, `change_type`, `stratum`,
`place`, `label_source` (`agreed`/`adjudicated`), `annotator_a`, `annotator_b`, `annotators_disagree`
(boolean), `min_lat`/`max_lat`/`min_lon`/`max_lon`, `group_by`
(`label`/`change_type`/`stratum`/`aoi`/`governorate`/`place_en`/`label_source`), `lang`. Every categorical
filter accepts Arabic or English, case-insensitively.

**Output summary:** `n_blocks`, unweighted and design-weighted change share (uncertain blocks excluded from
the share), optional `groups` when `group_by` is set; an unknown filter value returns
`{found: false, error: "unknown_filter_value", valid_values: [...]}` rather than a silent empty result.

**Caveats beyond the standard 4:** none additional.

**Example question:** "Which blocks still require human review?" (`annotators_disagree=true`, or see
`audit_status.interpretation_sensitive_blocks` for the human-audit version.)

---

## `blocks_near`

**Purpose:** reference blocks whose centre lies within a radius of a WGS84 point, nearest first, with
distances — a spatial-index lookup (exact brute-force result, verified in `test_blocks_near_index_exact_and_errors_R27`).

**Inputs:** `lat`, `lon` (required), `radius_km` (default 1, max 50), `label` (optional filter, either
language), `limit`, `lang`.

**Output summary:** `blocks` (list of `{id, distance_km, label, ...}`, nearest first), `labels` (counts),
`n_blocks`; explicit `error: "out_of_range"` / `"bad_coordinates"` for invalid input.

**Caveats beyond the standard 4:** distances are to sampled block centres only, not a continuous surface.

**Example question:** "What reference blocks are within 2 km of this point?"

---

## `area_estimate`

**Purpose:** the design-weighted share of blocks with change in an AOI (`beirut`/`mount_lebanon`) and/or
governorate, with a stratified-bootstrap 95% confidence interval — the pre-audit, AI-consensus figure.
For the audit-corrected version of this number, use `audit_status` instead.

**Inputs:** `aoi`, `governorate` (both optional — omit both for the full sample), `lang`.

**Output summary:** `share_change_weighted`, `ci95_bootstrap` (2-element interval).

**Caveats beyond the standard 4:** this is the raw, **uncorrected** estimate; `audit_status`'s
`audited_area_estimate_km2` is the one the thesis treats as primary from Section 5.14 onward.

**Example question:** "How much changed area was estimated?" (pre-audit); "...after the audit?"
(`audit_status`).

---

## `audit_status`

**Purpose:** the completed Appendix G blind two-reviewer human audit in one call — sample size and
agreement, which blocks' audited label differs from the AI-consensus label (both the broad list and the
13 pre-registered "Rule 1 certainty units"), the correlated-error test (Rule 2) result, and the resulting
audited re-analysis (headline spectral-vs-random-forest-vs-DINOv2 AUC comparison and the recalibrated
changed-area estimate). Every value is read from the audit's own result files
(`human_audit_results.csv`, `human_audit_key_R26.csv`, `appendix_g_rules23_R38.json`,
`audited_primary_reanalysis_R38.json`) — nothing is recomputed by this tool.

**Inputs:** `lang` only.

**Output summary:** `n_audited` (80), `n_decided` (75), `n_interpretation_sensitive_undecided` (5) and
`interpretation_sensitive_blocks`; `reviewer_agreement_n`/`rate`;
`blocks_where_audited_label_differs_from_ai_consensus` (17 blocks); `rule1_certainty_units`
(`n_units: 13`, `flipped_block_ids: ["E137", "E199"]`, with a `meaning` field distinguishing this from the
broader 17-block list); `correlated_error_test` (`fires`, error-rate estimates, gap in percentage points);
`audited_headline_auc` (spectral/random_forest/dinov2 AUC, the spec-minus-rf gap and its 95% CI,
`conclusion: "not_supported_audit_sensitive"`); `audited_area_estimate_km2` (corrected/uncorrected,
per-AOI breakdown); a bilingual `message` summarising all of the above in one paragraph.

**Caveats beyond the standard 4:** `note` states this audit covers only the 80-block decision-sensitive
subset, not the full 200-block sample.

**Example questions:** "How much changed area was estimated after the audit?"; "Why is the spectral vs.
random forest claim audit-sensitive?"; "قديش المساحة المتغيّرة بعد التدقيق البشري؟"

See [docs/audit-methodology.md](audit-methodology.md) for the full audit protocol these numbers come from.
---

## `map_catalog`

**Purpose:** list the 5 static "executive defense map" PDFs/PNGs (generated once by `make_maps.py` in the
full thesis/GIS bundle) — title, local path, what each map shows, the thesis section it illustrates, when
to open it in a defense, its one-line talking point, and its caveat. See
[docs/visual-demo.md](visual-demo.md) for the full map set and defense flow.

**Inputs:** `lang` only.

**Output summary:** `n_maps` (5), `maps` (list of `{id, title, path_pdf, path_png, exists, what_it_shows,
thesis_section, use_when, talking_point, caveat}`, in defense order), a `note` that the map files
themselves live in the full local thesis/GIS bundle, not this repository.

**Caveats beyond the standard 4:** `exists` is checked fresh against the local filesystem on every call —
it is `false` wherever the map files are not present (e.g. running this tool layer from this repository
alone, without the full bundle).

**Example question:** "What maps are available for the defense, and in what order should I show them?"

---

## `block_demo`

**Purpose:** a single, defense-ready summary for one block id, for use alongside `map_catalog()`'s maps:
its AI-consensus label, its human-audit label and agreement status if audited, whether it is one of the
13 pre-registered Rule 1 "certainty units", whether it is one of the 2 pivotal Rule 1 flips (`E137`,
`E199`), whether it is one of the 5 still-contested interpretation-sensitive blocks, which map(s) show it,
its change-type evidence-book image reference if any, and a plain-language
`professor_friendly_explanation` sentence for someone unfamiliar with the project's internals.

**Inputs:** `block_id` (required, `E001`..`E200`), `lang`.

**Output summary:** `ai_consensus_label`, `human_audit` (same shape as `block_evidence`'s field),
`agreement_status`, `is_rule1_certainty_unit`, `is_rule1_pivotal_flip`, `is_interpretation_sensitive`,
`why_it_matters`, `map_references` (titles of the relevant maps from `map_catalog()`),
`evidence_book_reference`, `professor_friendly_explanation`.

**Caveats beyond the standard 4:** every field is read from `block_evidence()`/`audit_status()`'s own
underlying data — this tool computes nothing new.

**Example questions:** "What's the defense-ready summary for E137?"; "Which blocks are still contested
after the audit?" (call for each of `E056`, `E080`, `E120`, `E123`, `E180`).
