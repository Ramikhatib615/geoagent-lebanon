# 5-minute live demo script (map-aware defense flow)

A timed script for demonstrating the agent visually to someone who has not lived inside this project —
a professor, a committee member, a reviewer. Pairs each step with what to show and what to say. Run
against a live MCP client (e.g. Claude Desktop, see [README.md](../README.md#claude-desktop-mcp-setup))
or `tool_cli.py`; open the map file named at each step from the full local thesis/GIS bundle (see
[docs/visual-demo.md](../docs/visual-demo.md) for why the map files themselves are not in this repo).
Total run time: about 5 minutes.

---

### 0:00 – 0:30 · Open on the study area

**Show:** Map 1 — Study Area & Sampling Frame.

**Say:** "This is a stratified sample, not a census: 200 blocks of 420 metres each, 100 in Beirut and 100
in Mount Lebanon, drawn by land-use stratum. Everything the agent says is grounded in these 200 blocks —
nothing outside them."

**Tool call:** `map_catalog()` — point out `thesis_section: "Section 3.2 (Sampling Design)"`.

---

### 0:30 – 1:15 · How the blocks were first labelled

**Show:** Map 2 — AI-Consensus Change Labels.

**Say:** "Every block starts with an AI-consensus label — two independent AI annotators plus adjudication
on disagreement — comparing Sentinel-2 composites from 2018 and 2025. 47 blocks show change, 135 show no
change, 18 are uncertain. This is a candidate label, not yet human-verified."

**Tool call:** `change_summary("beirut")` or `query_blocks(group_by="label")` to read the same counts live.

---

### 1:15 – 2:15 · The human audit and the two blocks that matter

**Show:** Map 3 — Human Audit Result, with E137 and E199 highlighted in bright blue with a star.

**Say:** "80 of the 200 blocks — the ones the thesis's own sensitivity analysis flagged as
decision-sensitive — went through a blind, two-reviewer human audit. 75 were decided; reviewers agreed on
every one of those 75. Two blocks, E137 and E199, both AI-consensus 'change', were both audited down to
'no change' by both reviewers. These two are pre-registered 'Rule 1 certainty units' — fixed before any
review started — and this pair flipping is the whole reason a headline model-ranking claim later becomes
audit-sensitive."

**Tool call:** `block_demo("E137")` then `block_demo("E199")` — read `why_it_matters` and
`professor_friendly_explanation` aloud.

---

### 2:15 – 2:45 · The numeric backbone

**Say:** "Here's the same story as one call."

**Tool call:** `audit_status()`. Point at: `n_audited: 80`, `n_decided: 75`,
`reviewer_agreement_rate: 1.0`, `rule1_certainty_units.flipped_block_ids: ["E137", "E199"]`,
`correlated_error_test.fires: true`, `audited_headline_auc.conclusion: "not_supported_audit_sensitive"`.

---

### 2:45 – 3:30 · What this means operationally

**Show:** Map 4 — Operational Deferral Map.

**Say:** "If this ran as a real pipeline, about a fifth of blocks — 43 of 200 — would still need a human:
label uncertain, or the two AI annotators disagreed and needed adjudication. This is not a fully autonomous
system, and the maps say so on their face."

**Tool call:** `uncertainty("mount_lebanon")` or `audit_status()`'s note on scope.

---

### 3:30 – 4:00 · Bilingual by design

**Say:** "The agent is Arabic and English natively, not translated after the fact."

**Ask (in Arabic):** "قديش المساحة المتغيّرة بعد التدقيق البشري؟"

**Tool call:** `audit_status(lang="ar")` — the same 56.6 km² / 82.1 km² figures, in Arabic, with Arabic
caveats.

---

### 4:00 – 4:45 · Close on the corrected headline

**Show:** Map 5 — Audit-Corrected Interpretation.

**Say:** "The audit-corrected changed area is 56.6 square kilometres — down from an uncorrected 82.1. And
the reason the spectral-vs-random-forest ranking is reported as audit-sensitive rather than a confirmed
result is exactly these same two blocks, E137 and E199, flipping under review. Two blocks out of two
hundred is what the whole finding rests on — which is precisely why we audited before claiming a
winner."

**Tool call:** `map_catalog()` again, or `block_demo("E056")` to show one of the 5 blocks that remain
genuinely contested even after the audit (the two human reviewers themselves could not agree).

---

### 4:45 – 5:00 · Limitations, stated plainly

**Say:** "Four things this agent will not claim: that 200 blocks cover all of Beirut or Mount Lebanon;
that an AI-consensus label outside the 80-block audit is human-verified; that the 5 still-contested blocks
have a settled answer; or that any tool here can create, adjudicate, or edit a label. It's read-only end
to end, and every number it gives you traces back to a specific file and block id."

---

## Quick reference: tool ↔ moment

| Moment | Tool |
|---|---|
| Study area | `map_catalog()` |
| AI-consensus counts | `change_summary`, `query_blocks` |
| The two pivotal blocks | `block_demo("E137")`, `block_demo("E199")` |
| Audit summary | `audit_status()` |
| Operational deferral | `uncertainty()` |
| Arabic | any tool with `lang="ar"` |
| A still-contested block | `block_demo("E056")` (or E080 / E120 / E123 / E180) |
