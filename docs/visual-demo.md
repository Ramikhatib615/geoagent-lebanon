# Visual demo: the map-aware defense flow

This repo's tool layer is not only text: two read-only tools (`map_catalog`, `block_demo`) let the agent
point a professor or reviewer at the right static map and the right block at the right moment in a
defense, instead of leaving them to interpret a table of 200 rows on their own. This document explains
the visual sequence; see [examples/visual_demo_script.md](../examples/visual_demo_script.md) for a
ready-to-run 5-minute script and [docs/mcp-tools.md](mcp-tools.md) for the two tools' full reference.

## Why this exists

A reviewer who has not lived inside this project for months cannot be expected to hold 200 reference
blocks, 80 audit rows, and a dozen report sections in their head at once. The executive map set and these
two tools exist to compress that into five clean pictures and a handful of named blocks worth
remembering — without changing a single number the project report reports. `map_catalog()` and `block_demo()` are
read-only lookups over the same result files every other tool in this repo already reads; they compute
nothing new.

## The executive map set (`make_maps.py`, repo root of the full project bundle)

Five static PDF/PNG maps, generated once from the same reference and audit files this repository ships,
each with a title, subtitle, legend, north arrow, scale bar, and a source/caveat note:

| # | Map | Report section | One-line purpose |
|---|---|---|---|
| 1 | Study Area & Sampling Frame | Section 3.2 (sampling design) | Where the two AOIs are and how the 200-block sample was drawn |
| 2 | AI-Consensus Change Labels | Chapters 3–4 (Data & Methods) | The original, pre-audit label for all 200 blocks |
| 3 | Human Audit Result | Section 5.3.4 & Appendix G | The 80 audited blocks: agreed, contested, and E137/E199 highlighted |
| 4 | Operational Deferral Map | Section 5.15 | What a deployed pipeline would decide automatically vs. send to a human |
| 5 | Audit-Corrected Interpretation | Sections 5.13–5.14 & 6.6 | The audit-corrected 56.6 km² headline and why the model-ranking claim is audit-sensitive |

**These map files are part of the full local project GIS bundle, not this GitHub repository** — the same
boundary this repo already draws around raw imagery and the ArcGIS Pro project (see
[data/README.md](../data/README.md)). `map_catalog()` reports each map's local path, title, project report
section, and talking point, and checks `exists` fresh on every call; it never claims a file is present
that it cannot actually see.

## The two tools

- **`map_catalog(lang)`** — the 5 maps above, in defense order, each with `title`, `path_pdf`/`path_png`,
  `exists`, `what_it_shows`, `report_section`, `use_when`, `talking_point`, and `caveat`.
- **`block_demo(block_id, lang)`** — a single-block defense card: the AI-consensus label, the human-audit
  label and agreement status if audited, whether it is one of the 13 pre-registered Rule 1 "certainty
  units", whether it is one of the 2 pivotal Rule 1 flips (E137, E199), whether it is one of the 5 still
  -contested interpretation-sensitive blocks, which map(s) show it, its change-type evidence-book image
  reference if any, and a plain-language `professor_friendly_explanation` sentence.

## The consistent map styling

The same palette and outline convention runs across all 5 maps and matches what `block_demo()` calls out
in `why_it_matters`:

- **Red** — `change`
- **Gray / green** — `no_change`
- **Amber** — `uncertain` (Map 2) or deferred-to-human (Map 4)
- **Purple** — contested / interpretation-sensitive blocks (the 5 undecided: E056, E080, E120, E123, E180)
- **Bright blue outline + star** — E137 and E199, the two decisive Rule 1 flips, on every map where they
  appear
- **Thick black outline** — audited (the 80-block sample); **thin, light outline** — not audited
  (AI-consensus only, the remaining 120 blocks)

## The defense flow

A recommended path through the material, each step handed off from one map/tool to the next:

1. **Map 1 — Study Area & Sampling Frame.** Orient the room: two AOIs, 200 stratified blocks, before any
   result is shown.
2. **Map 2 — AI-Consensus Change Labels.** How the blocks were first labelled — two AI annotators plus
   adjudication — before any human touched them.
3. **Map 3 — Human Audit Result.** The 80-block two-reviewer audit: what was confirmed, what was contested, and
   E137/E199 called out as the two blocks that matter most.
4. **`audit_status()`.** The numeric backbone behind Map 3: agreement rate, the correlated-error test, the
   audited AUC comparison, and the corrected area estimate — all read from the audit's own result files.
5. **Map 4 — Operational Deferral Map.** Turn the audit into an operational claim: what fraction of
   decisions a deployed pipeline could make on its own vs. send to a person.
6. **An Arabic question** (e.g. "قديش المساحة المتغيّرة بعد التدقيق البشري؟") to demonstrate the agent is
   bilingual by design, not by a translation layer bolted on afterward.
7. **Map 5 — Audit-Corrected Interpretation**, closing on the headline: 56.6 km² corrected (was
   82.1 km² uncorrected), and why two blocks flipping is what makes the spectral-vs-random-forest ranking
   audit-sensitive rather than a confirmed result.
8. **Limitations**, stated plainly: a 200-block stratified sample, not full coverage; AI-consensus labels
   are candidate labels outside the 80-block audit; 5 blocks remain genuinely undecided even after the
   audit; the agent is read-only end to end.

See [examples/visual_demo_script.md](../examples/visual_demo_script.md) for this flow written out as a
timed, line-by-line script.
