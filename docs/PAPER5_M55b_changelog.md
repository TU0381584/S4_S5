# M55b — fix M55's regression, get the real reduction from prose (25pp → 23pp; target 20pp not reached)

## Status: NO RIG, complete (LaTeX-only). Target: `Papers_4-5/Paper_5/WPC/main.tex` @ M55's `33d4180`. Compiles clean at every stage and at the final canonical sequence (pdflatex → bibtex → pdflatex ×2, exit 0 every stage, zero undefined references or citations). **Final page count: 23pp** — down 2pp from M55's 25pp regression, but 3pp short of the ~20pp target. Reported honestly per the gate's own instruction not to force further cuts below the target or past a finding.

## Root-cause fix confirmed

M55's own diagnosis was correct: Group A's `tab:related` (6 columns, 2 wide free-text) and Group C's `tab:safeguards` (4 wide free-text columns) cost more rendered space at `\small` than the prose they replaced. This gate reverted the first to compressed prose and rebuilt the second as a short-cell table, per the milestone's own two options.

## Per-group measured page counts (after 2 pdflatex passes following each group/sub-step; final row is the canonical 4-stage compile)

| checkpoint | pages | Δ vs. previous |
|---|---|---|
| Starting point (M55's `33d4180`) | 25 | — |
| After Group F (Related Work table → prose) | 25 | 0 (real savings made; see note below) |
| After Group G (safeguards table → short cells) | **24** | **−1** |
| After Group H1 (§8 Live Deployment compression) | 24 | 0 (real savings, no boundary crossed) |
| After Group H2 (§5 diagnosis compression) | 24 | 0 |
| After Group H3 (§6.3 disruption prose) | 24 | 0 |
| After Group H4 (§7/§9 scaling prose) | **23** | **−1** |
| After Group H5 (abstract/intro/conclusion) | 23 | 0 |
| **Final (canonical 4-stage compile)** | **23** | **net −2pp vs. M55's 25pp; −1pp vs. the original 24pp baseline** |

**Note on Group F's measured 0pp**: the raw page count did not drop after F alone, but a direct check of the document's own pagination (`pdftotext`, tracking where References/Declarations begin) showed the Declarations block moved from starting on page 23 back to page 22 after F — real, sub-page savings that only crossed a full page boundary once G's own savings stacked on top. This is the same "savings accumulate before crossing a boundary" pattern seen repeatedly in M55 itself; verified directly rather than assumed.

## Group F — Related Work table → compressed prose

Removed `Table~\ref{tab:related}` and its one referring sentence.
Replaced with the original systematic-review framing sentence (kept,
unedited) + one paragraph clustering the seven prior-art works into
three groups exactly as specified: Shao/Ahmadi/Sulaiman (GA/MA slicing
and admission control, neither metric-masking check nor replication),
Tashman/Fatehi (disruption robustness, neither metric-trust check nor
replication), Zhang/Yasin (FL/FL+DP, no correctness-aware quality
check / different threat model) — plus the two-of-three-pillars group
and the original closing "not a new design-space point but a
demonstration" sentence, both restored verbatim. Every citation key
preserved (shao2021gatmarl, ahmadi2024generalizable,
sulaiman2023coordinated, tashman2026adversarial,
fatehi2026attentionmarl, zhang2022federatedoran, yasin2025dpfl,
mohajer2026pronto, bouroudi2025gnnmarl, qasim2025tgnnfl,
gong2026femaddpg) and every distinguishing claim preserved (Ahmadi's
and Sulaiman's topology-generalisation question vs. our fixed-topology
integrity question, cross-referencing Section~\ref{sec:results-m6};
Zhang's own periodic-sync-precedent claim; Yasin's different threat
model and the $\sigma$-sweep cross-reference). The new paragraph is
one block (4 sentences), shorter than both the original 6 paragraphs
and the table+synthesis that replaced them.

**Preamble cleanup**: confirmed `\makecell` was used only in
`tab:related`'s header (now removed) and `\cmark` only in that table's
"This paper" row (also removed); `\xmark` remains genuinely used in
`tab:disruption` (M55's Group B2). Removed `\usepackage{makecell}` and
the `\cmark` `\providecommand`; kept `\usepackage{pifont}` and
`\xmark`.

## Group G — safeguards table → short-cell form (G1, not reverted to prose)

G1 was measured to fit denser than prose, so G2 (full prose revert) was
not needed. Rebuilt `Table~\ref{tab:safeguards}` with plain `l` columns
(no fixed `p{}` widths) and short-cell content, e.g. "compliance scores
an always-accept no-op no worse than correct behaviour" →
"Compliance blind to no-op"; "Config-level review cannot see a
cross-layer scheduler floor" → "Can't see cross-layer floor". All four
failures and their outcomes are intact: training collapse
(0/30$\to$21/30), eval-log contamination (logs cleared, no retrain),
reproducibility gap (churn claim retracted), scheduler-floor bug
($>$100k readings clear). Dropped the redundant `(Fig.~\ref{fig:collapse})`
pointer from the Outcome cell (the figure is still cross-referenced
from the prose two paragraphs later).

**Measured effect: −1pp** (25→24, crossing a real page boundary).

## Group H — prose compression

**H1 (§8 Live Deployment, ~750→~480 words)**: Compressed all five
paragraphs to findings-only, cutting re-explanation and hedging
repetition while preserving every claim and every number: the
cross-layer floor-bug mechanism (below-5-PRB grants), fixed at root
(commit `cda9d65`), $>$100,000 clear scheduler-state readings, all
three slices ~100% served / 0.000% loss at both 1 and 2 UEs, the
deployability-not-contention headline claims (both bolded sentences
kept), the unit-mismatch standing finding with its exact $-47.64$ vs.
$-1{,}002{,}377.5$ (21,000$\times$) numbers, and the retired-
recalibration paragraph. Dropped only the redundant exact-calendar-date
parentheticals on the two commit references (the commit hashes
themselves, `82b20f6`/`40ae2f3`/`cda9d65`, are all still present and
traceable) and repeated framing clauses ("This rig, at every native
load level it has been tested at, has never been shown to reach..."
type restatements collapsed to state each fact once).

**H2 (§5 diagnosis prose)**: Compressed the collapse-discovery,
two-fixes, and append-log paragraphs further (each to fewer, denser
sentences), and lightly compressed the two-metrics intro paragraph and
the section's own opening. Left the magnitude-encoding paragraph
(cosine 0.99997, the mechanism sentence) and the 44/49 (89.8%)/21/24
(87.5%) disagreement paragraph completely untouched, as both M55 and
this gate's own standing protection require.

**H3 (§6.3 disruption prose)**: Trimmed the independent-DQN
churn-retraction paragraph's redundant number restatement (the
replication-sample triple and its seed-range descriptor, both already
in `Table~\ref{tab:replication}`, replaced with a direct table
cross-reference) while keeping the full retraction narrative, the
$p=0.084/0.106/0.065$ committed-sample detail (not otherwise tabulated,
so kept), the federated-arm regeneration provenance note (untouched),
and the single-severity formal Wilcoxon result (untouched, outside
this edit's range).

**H4 (§7 + §9 scaling prose)**: Compressed the three-sample-convergence
narration in §7 (N=19) to the finding, keeping the 31%/78%/49-seed/
68-192/35.4% [25.5,45.8]/64-seed numbers and the "none of three samples
was wrong" epistemics in one sentence (previously two). In §9 (N=7),
removed the literal restatement of every cell already in
`Table~\ref{tab:m27-n7}` (91.7/75.0/41.7/58.3/0.0/16.7, etc.) from the
following paragraph, keeping only the cross-scale comparison number
that the table itself doesn't show (the N=19 pooled 35.4% [25.5,45.8]
GAT-CTDE is compared against) and every interpretive finding (pilot
overturned, GAT-CTDE's rate present from N=7, independent-DQN's
"rarely not never").

**Measured effect (H1-H4 combined): −1pp** (24→23, crossing one page
boundary after H4 specifically; H1-H3's real savings did not
individually cross a boundary but did not go to waste -- they reduced
how much H4's own savings needed to close the gap).

**H5 (Abstract + Intro + Conclusion)**: In the Introduction, compressed
the "two methodological safeguards" paragraph (which had grown
substantially redundant with the "three gaps, we close all three"
paragraph immediately above it, and with the now much more detailed
Evaluation Safeguards and Live Deployment sections) from ~180 to ~110
words, keeping every specific claim (30 campaign seeds, the disruption
retraction, the floor-bug-fixed-at-root + disclosed-stress-regime
confinement) with section cross-references replacing re-explanation. In
the Conclusion, trimmed connective phrasing from the scaling+live
paragraph ("a real cluster-size-specific effect", "rather than left
open", "on real hardware", "and re-collected") without touching any of
the four failures, the architectural finding, the 35.4%/N=7 claim, the
live-deployability claim, or any of the four limits (all confirmed
still present verbatim). In the Abstract, cut one redundant clause
("trained centrally and executed independently", restating what
"CTDE" already names). Reached the end of H5's scope at 23pp; did not
reach 20pp, so no sub-step was left unused for lack of need.

**Measured effect: 0pp** (real, sub-page savings; no boundary crossed
in the Abstract/Intro/Conclusion pass alone).

## Zero-number-changed verification

Diffed every numeric token in `main.tex` before vs. after this gate
(same method as M55's own verification) and manually traced every
flagged asymmetry:

- The removed-table's own column-width specifiers (`1.9cm`, `2.5cm`,
  `3.1cm`, etc., appearing as bare `1.9`/`2.5`/`3.1` etc. in the diff)
  disappeared because `tab:related` itself was removed in Group F --
  LaTeX formatting parameters, not data.
- Every genuine data number flagged as "only removed" by the naive
  diff (0.0020, 0.097, 0.657, 1.223, 100,000, 16.7, 19, 33.3, 41.7,
  50.0, 58.3, 66.7, 75.0, 83.3, 91.7, 900, 909, 1000, 35, 51, etc.) was
  individually confirmed, by direct grep against the current file, to
  still be present at least once -- each flagged instance is a
  legitimate de-duplication (H3's and H4's own table cross-references)
  reducing a repeated count from 2+ to 1, never to 0.
- The two dropped exact calendar dates (2026-07-16, 2026-08-19) on the
  floor-bug commit references are provenance metadata, not findings;
  the commit hashes themselves (`82b20f6`, `40ae2f3`, `cda9d65`) that
  actually identify the fix remain present and grep-confirmed.

**No number changed value.** Every figure in the rewritten manuscript
still matches its `docs/PAPER5_M49_reproducibility_manifest.csv` /
`docs/PAPER5_M54_claim_artifact_table.csv` row.

## Remaining overage: why 20pp was not reached, and the least-harmful next candidate

**23pp final, 3pp above the ~20pp target.** Diagnosed directly by
checking where `Acknowledgements`/`Declarations`/`References` begin
(`pdftotext`-based pagination check): all three now start on the same
page (21), meaning the paper's own body content (Introduction through
Conclusion) occupies almost exactly 20 pages already, and the
**bibliography's own 21 DOI-linked entries need very close to 2.3
further pages on their own**, essentially independent of how much more
body prose is cut. Cutting the body by one more full page (to ~19
pages) would shift the tail to start on page 20 and finish around page
22 -- not a further full page of visible savings for each page of body
cut, because the bibliography's fixed footprint dominates the
remainder. Reaching a literal 20pp total through body-prose compression
alone, without touching the bibliography's own formatting or any
finding, does not appear achievable with the sections this gate's
groups authorized.

**Least-harmful remaining candidate (not attempted here, not
authorized by this gate's own groups)**: tighten the bibliography's own
typesetting rather than cut more prose -- e.g., dropping the full
`https://doi.org/...` URL prefix in favour of a bare DOI string, or a
more compact `\bibliographystyle`, could plausibly recover most of the
~1pp still needed on its own, since it is pure formatting economy (the
DOI itself, still traceable, is unaffected) and touches zero findings,
numbers, or prose. This was not attempted since it falls outside
Groups F/G/H as specified and changes reference-list typesetting rather
than manuscript prose.

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>
# → no matches
```

Compiled and verified after every group/sub-step (F, G, H1, H2, H3,
H4, H5) individually and once more at the end as the canonical 4-stage
sequence. 23 pages, `main.pdf` regenerated.

## STOP

Reported per the milestone's own gate. Final page count: **23**
(down from M55's 25pp regression and 1pp below the original 24pp
baseline; target ~20pp not reached). Overage and the recommended,
not-yet-authorized next candidate (bibliography typesetting) reported
above, per the gate's own instruction not to cut a finding to force the
number. Awaiting review before any further condensation pass.
