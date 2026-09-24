# M55 — condensation changelog (24pp → 25pp; target ~20pp not reached)

## Status: NO RIG, complete (LaTeX-only). Target: `Papers_4-5/Paper_5/WPC/main.tex`. Compiles clean at every stage (pdflatex → bibtex → pdflatex ×2 after the full group sequence, exit 0 every stage, zero undefined references or citations). **Final page count: 25pp — 1 page MORE than the 24pp starting point, not the ~20pp target.** Reported honestly per the gate's own instruction ("If still >20pp... report the overage instead" of cutting a finding to force the number).

## Preamble

Added, guarded with `\providecommand` (not `\newcommand`) so a
double-inclusion cannot error:
```
\usepackage{pifont}
\usepackage{makecell}
\providecommand{\cmark}{\ding{51}}
\providecommand{\xmark}{\ding{55}}
```

## Per-group page counts (measured after 2 pdflatex passes following each group; final canonical count after the full bibtex+2×pdflatex sequence at the end)

| checkpoint | pages | Δ vs. previous |
|---|---|---|
| Baseline (M54 delivery) | 24 | — |
| After preamble + Group A | 25 | **+1** (target was $-$0.7) |
| After Group B (B1+B2) | 25 | 0 (target was $-$1.3) |
| After Group C | 25 | 0 (target was $-$0.9) |
| After Group D | 25 | 0 (target was $-$0.6) |
| After Group E | 25 | 0 (target was $-$0.5) |
| **Final (canonical 4-stage compile)** | **25** | **net +1 vs. baseline, against a $-$4.0 target** |

## Group A — Related Work → comparison table

Replaced the six prior-art comparison paragraphs (from "The canonical
result behind..." through "...the resulting numbers mean.") with the
existing systematic-review framing sentence (kept, unedited) +
`Table~\ref{tab:related}` (Work / Setting / Focus / Metric-mask. /
Indep. seed / Live deploy., 7 prior-art rows all \xmark + "This paper"
all \cmark) + a 4-sentence synthesis. Every citation key preserved
(shao2021gatmarl, ahmadi2024generalizable, sulaiman2023coordinated,
tashman2026adversarial, fatehi2026attentionmarl, zhang2022federatedoran,
yasin2025dpfl, plus the two-of-three-pillars group
mohajer/bouroudi/qasim/gong, now in the lead sentence before the
table). Every distinguishing claim preserved: Ahmadi/Sulaiman's
topology-generalisation question vs. our fixed-topology integrity
question; Tashman/Fatehi's robustness-without-metric-trust gap; Zhang's
no-DP/no-quality-check gap (plus its own periodic-sync-precedent
claim, folded into the table's Focus column); Yasin's different threat
model.

**Measured effect: +1pp, opposite of the $-$0.7pp target.** The
6-column table (two of them wide text columns, `p{1.9cm}`/`p{2.5cm}`/
`p{3.1cm}`) costs more vertical space at `\small` than the fairly
dense original prose saved, once caption and rule overhead are
included — the "table is always more compact than prose" assumption
does not hold when two of six columns need free text rather than a
short symbol or number.

## Group B — Disruption §6.3 → two tables

**B1**: Replaced the "Every headline paired comparison..." paragraph
with a 2-sentence lead (kept the GAT-CTDE dropout replication example,
+0.170/+0.552/+1.449 vs. +0.165/+0.601/+1.710, inline as instructed) +
`Table~\ref{tab:replication}` (4 rows: GAT-CTDE$-$indep reward,
GAT-CTDE$-$single-agent reward, federation cost, independent-DQN churn
cost flagged $\dagger$ as the one retraction).

**B2**: Converted the per-severity narrated triples into
`Table~\ref{tab:disruption}` (Arm × Dropout/Churn/Spike), keeping the
$p$-values and every finding as prose around the table: the churn
retraction narrative (both samples, "opposite of immune"), the
federated-arm regeneration provenance note (environment drift, still
in prose, not moved into the table), and the single-severity formal
Wilcoxon result (dropout 10% only, $p=0.0059$, untouched, outside
B2's edit range). Cells for arms with no individually-computed triple
in the original prose (independent DQN's and single-agent DQN's own
dropout costs; the qualitative "same super-linear pattern" statement
only) are marked $\dagger$ in the table rather than invented — no
number was fabricated to fill the grid.

**Measured effect: 0pp net.** The two tables plus the retained
provenance/retraction/formal-test prose paragraphs occupy essentially
the same space as the original narration; B1+B2 did not add pages, but
did not recover Group A's +1pp either.

## Group C — Evaluation Safeguards → summary table + trimmed diagnosis

Added `Table~\ref{tab:safeguards}` (4 rows: training collapse,
eval-log contamination, same-seed reproducibility gap, live
scheduler-floor bug — the last one forward-referencing
Section~\ref{sec:results-m8}, since that failure is diagnosed there,
not in this section). Compressed the collapse-diagnosis narration: the
magnitude-encoding paragraph (cosine 0.99997, the mechanism sentence)
kept verbatim as instructed; the LayerNorm→per-slice-Q-head
blow-by-blow reduced from 3 paragraphs to 2 sentences, keeping the
30/30→27/30→9/30 progression numbers (cross-referencing Fig.~2, which
already shows it) but dropping the specific 0/3-vs-1/3 pilot ablation
numbers (unprotected — absent from both Fig.~2 and the M54
claim-to-artifact table) while keeping the qualitative "not every
plausible variant helped" finding. The append-mode log-contamination
paragraph compressed from 6 sentences to 3, keeping the bug mechanism,
detection method, contamination scope, and fix. The 44/49 (89.8%) +
21/24 (87.5%) metric-disagreement result kept exactly as before,
untouched.

**Measured effect: 0pp net.** The new table's overhead roughly
cancelled the prose trimmed from the diagnosis narration.

## Group D — dedup the three-gaps framing + tighten abstract

Found the "no study checks metric-masking / replicates on independent
seeds / tests live contention" triad stated in full in the
Introduction (already the case pre-M55, correctly left as the single
full statement) and discovered Group A's own new synthesis sentence in
Related Work had, by construction, restated it a second time in full;
compressed that sentence to a cross-reference ("No work in
Table~\ref{tab:related} clears all three of the practice gaps the
Introduction names as this paper's own to close.") rather than leave
two full statements in the paper. Tightened the abstract (approx.
20–25% shorter by word count, not the full 30% target, since every
headline number had to stay): kept every headline result (decisive vs.
independent-learner; small/n.s. vs. single-agent; 35.4%
[25.5%,45.8%] collapse rate already present at 7 gNBs; FL-free;
DP threshold; disruption accelerates; 44/49 metric disagreement; live
deployability + cross-layer integrity finding), the "honest limit we
report rather than obscure" framing, and the deployability-vs-
contention distinction — all preserved verbatim or near-verbatim.
Compressed the architecture-description clauses and merged
overlapping "results + framing" sentences to remove re-explanation
already carried by the body.

**Measured effect: 0pp net at whole-page granularity** (the abstract
occupies a fixed fraction of page 1 regardless of moderate word-count
changes; the true saving is real but sub-page and did not cross a page
boundary).

## Group E — Conclusion trim

Compressed the FL+DP+disruption paragraph from 3 sentences with
several restated CIs/procedural details (the FedProx "0.03%... ten
times the round length" mechanism, already stated once in the Method
section) down to a 2-sentence one-liner, keeping the churn-retraction
claim as an embedded clause rather than dropping it. Removed the
restated "(31% vs. 78%)" parenthetical from the scaling paragraph —
these two numbers remain, unedited, in the Cluster-Size Scaling body
(`primary sample (31\%) and the replication sample (78\%)`, confirmed
present) — while keeping the 35.4% [25.5%,45.8%]/$N{=}7$-already-present
scaling claim and the live deployability + floor-bug integrity claim
verbatim. Left the four-failures sentence, the honest architectural
finding, and the four bounded limits (including the companion-paper
[11] pointer and the "stand independently of it" clause) unchanged, as
instructed.

**Measured effect: 0pp net at whole-page granularity** (real,
sub-page savings; Conclusion did not cross a page boundary either
direction).

## Zero-number-changed verification

Ran a full diff of every numeric token (git diff on `main.tex`,
before/after this milestone) and manually traced every token that
appeared unbalanced between removed and added lines:

- `31%`/`78%`: removed only from the Conclusion (Group E's own
  intentional de-duplication); **confirmed still present, unedited, in
  the Cluster-Size Scaling body** (line with "primary sample (31\%)
  and the replication sample (78\%)").
- `0.442`, and every other CI bound flagged by a naive per-line regex
  as "only removed" or "only added": traced to line-wrapping around
  LaTeX's `$-$` minus sign in the original multi-line prose; **manually
  confirmed via direct grep that every such value is present, unchanged,
  in its new table cell** (e.g., GAT-CTDE$-$single-agent row:
  `+0.195 [$-$0.017, 0.442], p=0.058`, matching the original exactly).
- `95` (the literal string "95% CI"): the label, not the numeric CI
  bounds, is dropped from individual table cells, relying on the
  Experimental Setup section's own already-standing, unedited
  statement that "All confidence intervals are 95% bootstrap
  percentile intervals" — no CI bound value itself changed.
- `100,000`: appears in the new Table~\ref{tab:safeguards} cell **in
  addition to**, not instead of, its original sentence in the Live
  Deployment section (both present, unchanged, confirmed by grep) —
  not a new number, a repeated cross-reference to an existing one.
- Every other flagged token (900/909/1000/1009, the 0.165/0.601/1.710
  and 0.078/0.246/0.585-style triples, etc.) is a table cell repeating
  a value that appears exactly once elsewhere in the same or an
  adjacent paragraph, confirmed by direct grep against the M54
  claim-to-artifact table (`docs/PAPER5_M54_claim_artifact_table.csv`)
  — every value present in the rewritten manuscript matches its listed
  manifest row exactly.

**No number changed value.** This was condensation, not re-analysis.

## Overage: which group to push further

The gate's own instruction is explicit: do not cut a finding to hit
the page target, report the overage instead. Reporting it: **final
page count is 25, one page MORE than the 24pp starting point**, against
a ~20pp target — a 5-page gap, not a rounding error.

The root cause, isolated by the per-group page tracking above, is
**Group A**: its 6-column table (`tab:related`), with two wide free-text
columns (Setting, Focus) across 8 rows, costs more rendered space at
`\small` than the six paragraphs of already-dense prose it replaced.
Group C's `tab:safeguards` (4 rows, 4 wide text columns) is the second
most likely contributor, for the same structural reason. Groups B, D,
and E each achieved real, if sub-page, savings but had no further page
boundary to cross once A had already added one back.

**Recommendation if pushed further**: Group A is the highest-value
target — either drop the "Setting" column (folding it into "Focus" as
a single free-text column, since the two currently overlap in content
for most rows) to cut the table from 6 to 5 columns, or move
`tab:related` to a `table*`-style full-width layout if the class
supports it, or reduce to `\footnotesize`. Group C's table is the
second candidate (dropping the "How a standard pipeline misses it"
column to a footnote per row would save one wide column). Neither
change would cut any finding — both tables' cell *content* would move,
not disappear, consistent with the standing constraint. This was not
attempted in this gate since it was not pre-authorized as a specific
edit group, and the gate's own instruction is to report the overage
rather than improvise further cuts.

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>
# → no matches
```

Compiled and re-verified after every group (A, B, C, D, E individually)
and once more at the end as the canonical 4-stage sequence. 25 pages,
`main.pdf` regenerated, 7 `table` environments balanced
(7 `\begin`/7 `\end`), no lost floats, no multiply-defined labels.

## STOP

Reported per the milestone's own gate. Final page count: **25**
(target ~20, not reached; overage and cause reported above, per the
gate's own instruction not to force further cuts). Awaiting review
before any further condensation pass.
