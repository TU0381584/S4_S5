# M54 — manuscript rewrite changelog

## Status: NO RIG, complete. Target: `Papers_4-5/Paper_5/WPC/main.tex`. Compiles clean (pdflatex → bibtex → pdflatex ×2, exit 0 every stage, zero undefined references or citations — logs at `/tmp/pdflatex_run3.log`). Every numeric edit below is paired with its `docs/PAPER5_M49_reproducibility_manifest.csv` row; no new number was invented, and every retained number was left untouched from its manifest-verified value.

This rewrite implements the M54 CONTEXT spec section-by-section, using
only M49/M49b/M49c-verified numbers. Structural changes (macro
removal, section reordering) are listed once at the top since they
touch multiple sections; numeric/content edits are listed per section
below in the order they now appear in the compiled manuscript.

## Structural changes (whole-document)

- **Removed** the `\prefixflag`/`\prefixinline` macro definitions
  (former lines 13–21) and every invocation site (former abstract,
  Introduction, and all three pre-fix Live subsections). Confirmed
  zero remaining occurrences (`grep -n "prefixflag\|prefixinline"
  main.tex` → empty).
- **Reordered**: the former "Extending the Recalibration to the
  Topology-Scaling Axis" subsection (nested, confusingly, under
  `\section{Live Single-gNB Anchor}`) is now its own
  `\section{Cluster-Size Scaling at $N=7$}`, positioned after the Live
  Deployment section, content fully replaced (see below). Its label
  (`sec:results-m27`) is unchanged, so every existing cross-reference
  to it still resolves.
- **Replaced** the three pre-fix Live subsections
  (`sec:results-m8`/`sec:results-m8-load`/`sec:results-m8-fix`) with
  ONE new section, `\section{Live Single-gNB Deployment}`, keeping only
  the first subsection's label (`sec:results-m8`) so the System Model's
  and Introduction's existing forward references still resolve. The
  other two labels (`sec:results-m8-load`, `sec:results-m8-fix`) and
  their figures (`fig7_live_3v6.pdf`, `fig8_live_recalibrated_fix.pdf`)
  are no longer referenced by the manuscript (files left on disk,
  unused, not deleted).
- Removed `fig9_m27_scaling_reframe.pdf`'s reference; the $N=7$ result
  is now reported as a table (`tab:m27-n7`) instead, since the old
  figure's own content (contaminated-vs-clean comparison) no longer
  applies once the recalibration dependency is dropped.
- Added one new bib entry, `paper6-companion` (`@misc`, note =
  "Companion work, in preparation"), cited once in the Conclusion.

## Title + Abstract

- Retitled from "GAT-CTDE: A Graph-Attention Architecture for
  Coordinated Multi-gNB Slice Admission Control" to "From Architecture
  to Evidence: Realising a Graph-Attention, Multi-Agent, Federated
  Slice Admission Controller Under Correctness-Aware Evaluation" — leads
  with delivery (realisation + evaluation) rather than the architecture
  name alone.
- Abstract rewritten to lead with the per-component realisation and
  correctness-aware evaluation framing, folds in the M35 89.8% ledger
  number (manifest row 3) as evidence the safeguards generalise, and
  replaces the removed pre-fix live-anchor sentence with the honest
  deployability/cross-layer-integrity framing (no manifest row — this
  is prose framing, not a new number; all underlying live numbers are
  cited in the Live Deployment section, manifest rows 18–20).
- No numeric values changed in the abstract; every number already
  present (35.4% [25.5,45.8], 64 seeds) matches manifest row 6
  unchanged.

## Introduction

- Restructured the contribution paragraph into an explicit
  gaps→delivers statement (three gaps named, three deliveries named),
  per the milestone's own instruction. No numbers changed.
- Kept the `cacs26-paper` citation (0.57ms round-trip, <20K params)
  exactly as already fixed at M49b-0 — this is fixed citation #1 of 3.
- Replaced the closing `\prefixinline`-flagged sentence with the new
  deployability/cross-layer-bug framing (no manifest row — prose,
  consistent with the Live Deployment section below).

## Related Work

- Unchanged. Already consistent with the new novelty framing (metric
  masking + replication discipline gaps); no recalibration-dependent
  claims existed here to remove.

## System Model

- Strengthened the "stress environment" sentence using M49b-1-1's live
  measurement (manifest row 18: all 3 slices ≈100% served, 0% loss, 3UE
  and 6UE native) to give it "full evidentiary backing" per
  `docs/PAPER5_M49b5_scaling_regrounding.md` §5's own recommendation.
  No number changed; a new number (essentially 100% served / 0% loss)
  is added, sourced directly from manifest row 18.

## GAT-CTDE Method

- Unchanged. No pre-fix or recalibration dependency existed here.
  FedProx null result (already correctly reported) untouched.

## Evaluation Safeguards (formerly "Evaluation-Integrity Findings: A
Training Collapse, Diagnosed and Fixed")

- Section retitled; label (`sec:collapse`) kept so all 5 existing
  cross-references resolve unchanged.
- Collapse diagnosis and append-only-log-bug narratives: **unchanged**,
  still real, uncontaminated findings.
- **Added** two new paragraphs at the end of the section (where
  `sec:correctness-metrics` already lived): (1) the M35 89.8% (44/49)
  metric-disagreement ledger, independently confirmed 87.5% (21/24) on
  a disjoint supplementary range — **manifest row 3**, exact match,
  no discrepancy; (2) the reproduction-vs-replication discipline
  stated once, generally, pointing to Section `sec:results-m4`'s own
  tally rather than duplicating its count (avoids a second, possibly
  inconsistent number appearing elsewhere in the paper).

## Multi-gNB Results — Centralised Campaign (M2)

- **Unchanged.** Table 1 numbers (compliance 0.151/0.049/0.115; reward
  14.062/12.601/13.867; block precision 0.952/0.901/0.987) already
  match **manifest rows 4–5** exactly; no edit needed.

## Multi-gNB Results — Federated Training and DP (M3)

- **Unchanged numerically.** Federation cost +0.133 p=0.8125 and DP
  threshold 1.000/1.000/0.834/0.584 match **manifest rows 8–9** exactly.
- **Added** one sentence reframing federation + FedProx together as a
  deployability answer (periodic sync sufficient; DP cost bounded and
  known), per the milestone's "M3/M7 as deployability answers"
  instruction. FedProx's own null result (manifest row 11) was already
  correctly stated in the Method section and is referenced, not
  restated, here.

## Multi-gNB Results — Disruption Resilience (M4)

- **Numeric correction**: the federated-arm churn cost was
  `+0.073/+0.240/+0.585`; corrected to **`+0.078/+0.246/+0.585`**, with
  an inline provenance note (regenerated post-hoc after the original
  per-seed logs were found missing; environment drift identified as
  the benign cause by elimination). Sourced from **manifest row 14**
  and `docs/PAPER5_M49c_m4_resolution.md` (verdict: BENIGN, cite the
  regenerated values).
- All other M4 numbers in this section (GAT-CTDE dropout/churn,
  independent-DQN churn retraction original+replication, spike
  signals, the one-severity formal dropout test) were already clean
  per **manifest rows 12, 13, 15, 16, 17** — no other edits needed.
  The churn-retraction narrative itself (the reproduction-vs-
  replication case study) is **unchanged**, already accurate.

## Cluster-Size Scaling (M6, N=19)

- Body text **unchanged** — the $N{=}19$ pooled numbers (single-agent
  100% 15/15, GAT-CTDE 35.4% [25.5,45.8], independent-DQN 0/36) already
  match **manifest row 6** exactly (this is the row that required a
  bootstrap-methodology fix to *this project's own new verification
  script*, not to the manuscript's already-correct number).
- **One phrase edited**: the independent-DQN "never fully collapses"
  aside used to point at the now-retired $N{=}19$ recalibrated number
  (3/36); it now points at the new $N{=}7$ replication-sample exception
  (2/12) instead — see next section. This removes the last
  recalibration dependency from the $N=19$ body.

## Cluster-Size Scaling at N=7 (formerly "Extending the Recalibration
to the Topology-Scaling Axis", M27)

- **Full content replacement.** Old content (an $N{=}19$ and $N{=}7$
  resample under the now-retired `RealisticServedKpmSource`) removed
  entirely. New content reports the clean-environment $N{=}7$ resample
  (`ClosedLoopKpmSource`, unmodified, no recalibration) from
  **manifest row 7**: single-agent DQN 91.7%/75.0%, GAT-CTDE
  41.7%/58.3%, independent-DQN 0.0%/16.7% (primary/replication),
  against the original 3-seed pilot (0% for all three arms).
- New Table `tab:m27-n7` replaces the old figure
  (`fig9_m27_scaling_reframe.pdf`, no longer referenced).
- Explicitly states "no recalibration of any kind" twice, satisfying
  the milestone's "zero dependency on retired recalibration"
  requirement.

## Live Single-gNB Deployment (formerly "Live Single-gNB Anchor" +
"Heavier Live Load" + "Recalibrating the Simulator to Match Live
Congestion" — three subsections merged into one section)

This is the single largest content change in the rewrite, per the
milestone's own framing ("biggest change").

- **M41 bug explanation** (one paragraph, as specified): the
  cross-layer scheduler-floor misconfiguration, its catastrophic
  symptom, the root-cause fix (commit `cda9d65`), and direct
  scheduler-state instrumentation confirming the floor is clear
  throughout every run in this section (>100,000 combined readings —
  arithmetic: 35,702 from manifest row 19 + 71,498 from manifest row
  20 = 107,200).
- **Re-collection findings**: the rig cannot reach genuine per-slice
  scarcity at native or double-native load — sourced from **manifest
  row 18** (M49b-1-1: ~100% served, 0% loss at both 3UE/6UE native).
  The deployability-vs-admission-control distinction is stated as the
  section's own headline finding (bolded in the manuscript), directly
  reflecting `docs/PAPER5_M49b5_scaling_regrounding.md` §5's framing
  recommendation.
- **Preserved unit-mismatch fix**: kept as a standing, load-independent
  finding, with the specific catastrophic-case numbers updated from
  the pre-fix framing ("a real, independently-documented backlog
  failure regime") to the post-fix re-collection reading (embb margin
  $-47.64$, ~21,000× smaller than the original $-1{,}002{,}377.5$) —
  sourced from **manifest row 19** (M49b-2) and
  `docs/PAPER5_M49b4_recalibration_retirement.md` §4's exact
  recommended revision.
- **Recalibration retirement**: stated in one paragraph (not deleted,
  not re-run), consistent with the standing constraint that the
  retired `RealisticServedKpmSource` anchors remain untouched evidence.
- **E2-loop-feasibility citation**: `cacs26-paper` (0.57ms round-trip,
  <20K params) — this is fixed citation #2 of 3, moved here from the
  now-removed old $N{=}27$ subsection's trailing sentence (previously
  citation appeared in that subsection; now appears here instead,
  total count of 3 across the paper is preserved).
- No `\prefixflag`/`\prefixinline` anywhere in the new section
  (confirmed by the whole-document grep above).

## Novelty (Conclusion, opening paragraph)

- Reframed from a 3-failure count to a **4-failure count**, adding the
  M41 scheduler-floor bug as the fourth hidden failure the paper's own
  discipline (now including direct live scheduler-state
  instrumentation) caught. This centers the novelty statement on: (i)
  per-component realisation (Introduction's gaps→delivers paragraph),
  (ii) correctness-aware evaluation exposing metric masking (Evaluation
  Safeguards' M35 ledger), and (iii) the **new** cross-layer integrity
  finding (Live Deployment section) — replacing the now-dropped
  retired-recalibration novelty candidate (candidate (iii) in
  `docs/PAPER5_M48_novelty_statement.md`, explicitly not used here per
  the milestone's instruction).

## Limitations (Conclusion, closing paragraph)

- Expanded from **two** limits to **four**, stated once: (1) offline-only
  multi-gNB/federated/disruption scope, unchanged from the original;
  (2) the offline stress regime is disclosed as harder than any
  reachable live congestion level — **new**, sourced from
  `docs/PAPER5_M49b5_scaling_regrounding.md` §5's own recommendation;
  (3) the graph models only gNB nodes, no MEC/edge-compute nodes —
  **new**, per the milestone's explicit instruction; (4) the synthetic
  single-operator federated privacy setting, unchanged from the
  original.
- Added the `paper6-companion` forward reference here, framed as
  independent (no dependency), per the milestone's "#6 REFERENCE"
  instruction.

## Reproducibility / Data Availability (Declarations)

- Replaced the placeholder ("available from the corresponding author
  on reasonable request") with the concrete M49 statement: Zenodo
  archive (~48.6GB, CC-BY-4.0, split offline/live deposits) and the
  pinned toolchain (Python 3.12.3, PyTorch 2.13.0+cu130, NumPy 2.5.1,
  SciPy 1.18.0) framed explicitly as a release strength, per the
  milestone's own instruction — sourced verbatim from
  `docs/PAPER5_M49_gate_report.md`'s "Release plan" section.
- Code availability statement updated similarly (GitHub URL/licence
  placeholders, consistent with the Data Availability entry).

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>
# → no matches
```

24 pages, `main.pdf` regenerated. Remaining pdflatex warnings
(underfull vboxes, hyperref "destination with the same identifier",
"Token not allowed in a PDF string") are pre-existing cosmetic
bookmark/formatting warnings, not compile failures — none references
an undefined label or citation.

## STOP

Reported per the milestone's own gate. Awaiting review before any
further manuscript action (submission, additional milestones, or
polish passes).
