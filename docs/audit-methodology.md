# Audit methodology

## Why an audit exists at all

Every one of the 200 reference blocks starts with an **AI-consensus label**: two independent AI
annotators each label the block, and a third AI adjudicator resolves any disagreement. This is fast and
covers the whole sample, but it is not human ground truth — it can be wrong, and the project's own
sensitivity analysis showed that some of its headline findings depend on a small number of specific
blocks. Rather than treat all 200 AI-consensus labels as equally reliable, the project's Appendix G runs a
**two-reviewer human audit (under a protocol that specified blinding)** on exactly the blocks whose label could change a reported conclusion.

## The 80-block decision-sensitive sample

The audit does not cover all 200 blocks — only an **80-block subset** flagged as decision-sensitive by the
project's sensitivity analysis (blocks where a label flip would plausibly change a reported number or
ranking). This is a deliberate scoping choice, not a shortcut: auditing all 200 blind, by two reviewers,
was not feasible, and the 80 were chosen specifically because they are where a labelling error would
matter most.

**This means:** a block outside the 80 has only ever had an AI-consensus label. `block_evidence()` marks
this explicitly (`human_audit.audited: false`), and no tool in this repository claims human ground truth
for those 120 blocks.

## The audit protocol

- **Blinding specified:** under the protocol, each of the two human reviewers labels every block independently, without
  seeing the AI-consensus label, the other reviewer's answer, or which "rule" (below) a block belongs to.
  The audit sheets were prepared without the AI labels; no contemporaneous log records that blinding was
  kept, so it is reported as specified, not verified.
- **Two reviewers, reconciled:** `human_1` and `human_2` are recorded per block; where they agree, that is
  the `human_final` label. Reviewer agreement was 75/75 (100%) among the blocks a final label could be
  reached for.
- **Interpretation-sensitive blocks:** 5 of the 80 (E056, E080, E120, E123, E180) remain genuinely
  undecided — the two reviewers looked at the same evidence and reached different conclusions on blocks
  that are ambiguous even to a human. These are reported as undecided, never silently resolved by
  majority, tie-break, or defaulting to the AI-consensus label.
- **75 of 80 decided; 17 of those differ from their AI-consensus label.** This 17-block list
  (`audit_status().blocks_where_audited_label_differs_from_ai_consensus`) is the full record of every
  audited disagreement — it is broader than, and should not be confused with, the Rule 1 set below.

## Rule 1: the pre-registered "certainty units"

Before any block was reviewed, the audit protocol **pre-registered** exactly 13 blocks as "certainty
units" (`outputs/eval/human_audit_key_R26.csv`, `certainty_unit == 1`) — fixed in advance specifically
because the project's headline spectral-vs-random-forest ranking claim depends on them:

- **8 pivotal no-change blocks** that the ranking's validity requires to hold as `no_change`: E103, E094,
  E033, E098, E037, E107, E077, E168.
- **5 Mount Lebanon-low-stratum change blocks** whose outcome determines the ranking either way: E040,
  E137, E199, E068, E117.

Of these 13, **exactly 2 flipped** in the audit: **E137 and E199**, both from AI-consensus `change` to
audited `no_change`. It is *this* flip — not the broader 17-block list above — that the project report treats as
the decisive evidence that the spectral-vs-random-forest AUC ranking is **not supported / audit-sensitive**
(`audit_status().audited_headline_auc.conclusion == "not_supported_audit_sensitive"`), because the audited
gap's 95% CI (−0.074, 0.338) crosses zero.

`tools.py` derives this set programmatically from the `certainty_unit` column rather than hardcoding
E137/E199, so it stays correct if a future audit round changes which blocks are affected.

## Rule 2: the correlated-error test

The audit also tests whether the AI annotators' errors are **correlated** rather than independent random
noise — if the two AI annotators tend to agree with each other on blocks that are actually wrong, that is
a more serious problem than isolated mistakes, because it means their agreement is not a reliable quality
signal. `audit_status().correlated_error_test` reports `fires: true` for this sample: the AI-agreed error
rate (17.74%) is substantially higher than the auditor's own estimated error rate (3.12%), a gap of ~14.6
percentage points — evidence that AI-annotator agreement alone should not be treated as ground truth,
reinforcing why the audit was necessary at all.

## The resulting audited re-analysis

With the audit's corrected labels applied where they differ from AI-consensus:

- **Changed area:** 56.6 km² (95% CI 29.7–87.9), down from the uncorrected 82.1 km² — Beirut 3.9 km²,
  Mount Lebanon 52.7 km².
- **Model comparison:** the spectral-vs-random-forest AUC gap becomes audit-sensitive
  (`not_supported_audit_sensitive`) rather than a confirmed result, because of the Rule 1 flip above.

All of these numbers are read directly from `outputs/eval/appendix_g_rules23_R38.json` and
`outputs/eval/audited_primary_reanalysis_R38.json` by `audit_status()` — nothing is recomputed in the tool
layer, so the numbers here will always match whatever those result files (and the project report itself) report.

## AI-level uncertainty vs. human-audit sensitivity — not the same signal

`uncertainty(place)` reports an **AI-level** deferral signal: annotator disagreement or conformal
non-coverage, decided entirely by the AI pipeline before any human ever reviewed the block. This is a
different question from whether a block is `interpretation_sensitive` in the human audit. Block **E056**
is the clearest example: the two AI annotators agreed easily (`uncertainty("E056").defer_to_human ==
false`), yet it is one of the 5 blocks the two *human* reviewers could not agree on. Do not treat
`uncertainty()`'s output as a stand-in for the human audit's findings, or vice versa — use `audit_status()`
for anything about the completed human audit specifically.
