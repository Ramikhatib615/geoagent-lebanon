# Demo script

A ready-to-run sequence for demonstrating the live agent (via an MCP client once the MCP server is
configured — see [README.md](../README.md#mcp-client-setup) — or via `tool_cli.py` with no LLM
needed at all). Each question below names the tool the agent should reach for and what a correct answer
should contain; full recorded outputs are in [examples/sample_outputs.md](../examples/sample_outputs.md).

1. **"How much changed area was estimated after the audit?"** → `audit_status`. Expect: 56.6 km² (95% CI
   29.7–87.9), explicitly down from the uncorrected 82.1 km², with a caveat that this is the
   audit-corrected figure.
2. **"What happened to E137 and E199?"** → `block_evidence` for each id. Expect: AI-consensus `change` for
   both; audited `human_final` = `no_change` for both; both reviewers agreed; a note that this pair drives
   Rule 1.
3. **"Why is the spectral vs. random forest claim audit-sensitive?"** → `audit_status`. Expect: audited AUC
   gap 0.132, 95% CI (−0.074, 0.338) crossing zero, conclusion `not_supported_audit_sensitive` — not a
   confirmed win for either model.
4. **"قديش المساحة المتغيّرة بعد التدقيق البشري؟"** → `audit_status(lang="ar")`. Expect: the same 56.6 km²
   figure and 82.1 km² uncorrected figure, in Arabic.
5. **"شو صار بـ E137 و E199؟"** → `block_evidence` (ar) for each id. Expect: the Arabic equivalent of #2.
6. **"وين لازم يروح الإنسان يراجع؟" / "Which blocks were contested in the human audit?"** → `audit_status`
   → `interpretation_sensitive_blocks`. Expect: E056, E080, E120, E123, E180 — the 5 blocks the two human
   reviewers themselves could not agree on, distinct from the 38 blocks where the two *AI* annotators
   originally disagreed (`query_blocks(annotators_disagree=true)`).
7. **"Explain the difference between AI-consensus labels and human audit labels."** → `audit_status` +
   `block_evidence`. Expect: AI-consensus = two AI annotators + adjudication, present for all 200 blocks,
   never itself human-verified; human audit = two-reviewer review (protocol specified blinding) of the 80 decision-sensitive
   blocks only, surfaced via `human_audit.audited: true`, and treated as primary where the two differ.
8. **"Compare spectral, random forest and DINOv2."** → `audit_status` → `audited_headline_auc`. Expect: the
   three models' audited AUC values and the spectral-minus-random-forest gap and its CI, with the same
   audit-sensitive caveat as #3.

## What a good answer always includes

- The specific block id(s), count(s), or file(s) behind the claim — never an unsourced number.
- An explicit caveat whenever the answer touches a sample rather than full coverage, or an AI-consensus
  rather than an audited label.
- A refusal or hedge, rather than a guess, for anything outside the 9 tools' data (e.g. a place with no
  reference blocks, or a block id outside E001–E200).

## What a good answer never does

- State a pre-audit number as if it were the audited one, or vice versa, without saying which is which.
- Claim human ground truth for a block outside the 80-block audit sample, or for one of the 5 still-undecided
  blocks inside it.
- Conflate `uncertainty()`'s AI-level deferral signal with the human audit's `interpretation_sensitive`
  flag (see [docs/audit-methodology.md](audit-methodology.md)).
