# M56 — fix table overflow, authorized cuts (23pp → 23pp; target 20pp not reached)

## Status: NO RIG, complete (LaTeX-only). Target: `Papers_4-5/Paper_5/WPC/main.tex` @ M55b's `4d95d99`. Compiles clean at every stage and at the final canonical sequence (pdflatex → bibtex → pdflatex ×2, exit 0 every stage, zero undefined references or citations, **zero remaining "Overfull \hbox" warnings**). **Final page count: 23pp** — Group I fixed all three table overflows with zero content change; Group J's six authorized cuts (J1-J6) removed real content without moving the measured page count, confirming the bibliography's own fixed footprint (established in M55b) is the actual remaining constraint, not body prose. Reported honestly per the gate's own instruction not to cut a load-bearing finding to force the number.

## GATE I — table overflow fix (formatting only)

Added `\usepackage{array}`. Converted the three overflowing tables from
plain `l`/`c` columns to fixed-width wrapping `p{}` columns exactly as
specified:

- `tab:safeguards`: `{@{}llll@{}}` → four `p{}` columns. First attempt
  at the literal prescribed widths (0.20/0.24/0.22/0.26\textwidth)
  still overflowed by 6.24pt (traced to the *default* `\tabcolsep`
  gaps LaTeX inserts between adjacent `p{}` columns, on top of the
  prescribed widths, not to any single word) — confirmed by testing
  `\footnotesize` first (no change in the overflow amount, ruling out
  a font-size cause) and only then reducing the four widths by 0.015
  each (to 0.185/0.225/0.205/0.245) to absorb the gap overhead, which
  cleared it completely.
- `tab:disruption`: `{@{}lccc@{}}` → four `p{}` columns at the
  prescribed widths; `\footnotesize` alone cleared its 4.759pt
  overflow (confirmed this one *was* a font-size-sensitive case, since
  the culprit was an unbreakable numeric string like
  `+0.165/+0.601/+1.710` not fitting its column at `\small`).
- `tab:replication`: `{@{}lll@{}}` → three `p{}` columns at the
  prescribed widths; no overflow was ever present here, confirmed
  after the edit.

No cell content changed in this group. Verified via
`grep -n "Overfull \\hbox"` on the final compile log: **zero matches**.

**Measured pages: 23** (unchanged from the M55b starting point — this
group was a pure formatting fix, not a size reduction).

## GATE J — authorized cuts

Ran J1 through J6 in order, compiling and measuring pages after each;
none crossed a page boundary individually, and the final total (23)
is unchanged from before Group J despite six real, verified cuts —
consistent with M55b's own diagnosis that the bibliography's fixed
footprint, not body length, is now the binding constraint (see below).

### J1 — demand-spike non-finding: CUT

Removed the "Spike thresholds?" column from `tab:disruption` entirely
(every cell was an identical \xmark, so the column carried no
differentiating information once the finding is stated in prose).
Replaced the spike paragraph's per-sample p-value narration (the
cross-arm $p\leq0.014$ reproduction claim and single-agent DQN's
sample-dependent $p=0.0020$/$p=0.084$ contrast) with one sentence:
"Demand spike does not corrupt decision quality on the volume-invariant
block-precision metric ... its apparent per-step reward gain is a
denominator artifact ..., not better decision-making." Removed the now
entirely-unused `pifont` package and `\xmark` command (confirmed zero
remaining uses first).

**Cut, not compressed**: the per-sample $p$-values ($p\leq0.014$,
$p=0.0020$, $p=0.084$ for spike specifically) and the table column are
gone. **Compressed and kept**: the qualitative finding itself (spike
doesn't corrupt decision quality; the reward signal is a denominator
artifact), now pointing to Fig.~\ref{fig:m4-disruption}(c) which still
shows the same data visually.

### J2 — FedProx null mechanism: CUT

Replaced the full mechanism narrative (per-round drift = 0.03% of TD
loss; a 10$\times$-round-length follow-up showing drift growing to a
mean 1.44% yet still bit-identical to FedAvg) with the milestone's own
prescribed one-sentence version: "FedProx earns no measurable dividend
at any tested strength, traced to per-round client drift being
negligible relative to the loss scale."

**Cut**: the 0.03%, 1.44%, and 10$\times$-round-length numbers (none
of which is a tracked manifest row -- `PAPER5_M49_reproducibility_manifest.csv`
row 11 tracks only the qualitative "bit-identical to FedAvg" claim,
which is retained). **Kept**: the FedProx setup/motivation sentence
(why it was tried, citing the M6-discovered heterogeneity) and the
null result itself.

### J3 — §5 diagnosis internals: CUT

Removed the embedding-geometry paragraph's raw numbers ($\ell_2$ norm
2.55, embedding norm 19.6, cosine similarity 0.99997) and the
methodology sentence describing how they were measured, replacing it
with one sentence stating the causal mechanism directly: "The
collapsed checkpoint's encoder embeds congestion almost entirely as
embedding magnitude rather than direction, and since the downstream
Q-head is roughly linear in its input, larger magnitude pushes
$Q(\text{accept})$ up faster than $Q(\text{reject})$... running
backwards from the reward's intent." Also removed the
LayerNorm-affine-ablation aside ("not every variant helped (one,
reverted, made results worse)...") from the two-fixes sentence.

**Note**: this reverses M55's own explicit protection of this exact
paragraph (which had required keeping cosine 0.99997 verbatim) --
done here because M56's own instruction explicitly named this
paragraph for cutting, on the stated reasoning that
`tab:safeguards` + Fig.~\ref{fig:collapse} now carry the failure and
the fix, making M55's earlier protection superseded by this gate's own
authorization.

**Cut**: 2.55, 19.6, 0.99997 (embedding-geometry detail); the
LayerNorm-affine-ablation numbers (0/3 vs. 1/3, already dropped at
M55b and confirmed still absent). **Kept**: the magnitude-encoding
causal mechanism (one sentence, as required) and the 30/30→27/30→9/30
collapse-count progression (unchanged, still cross-referenced to
Fig.~\ref{fig:collapse}).

### J4 — single-severity disruption Wilcoxon: REMOVED (full paragraph)

Removed the entire paragraph ("A formal paired Wilcoxon test on
(GAT-CTDE's cost − independent DQN's cost)... reaches significance
only once, at dropout at the mildest severity..."). Confirmed via grep
that its specific numbers (+0.0135, [0.0053, 0.0236], $p=0.0059$) are
not referenced anywhere else in the manuscript before removing it.

**Cut entirely**: this one-cell effect (+0.0135, 95% CI [0.0053,
0.0236], $p=0.0059$, "9 losses/0 ties/1 win") and its own
"real-at-one-severity, absent-everywhere-else" framing sentence. The
milestone's own instruction confirms this "carries no claim the paper
relies on" -- verified true by the absence of any other reference to
it.

### J5 — redundant cross-sample re-narration: COMPRESSED

Cut the lead-in clause "Every dropout and churn result above was
independently checked against the 1000--1009 sample and holds up in
direction and approximate magnitude" immediately before
`Table~\ref{tab:replication}`, since the table's own caption already
states the same comparison structure. Kept the specific, non-tabulated
GAT-CTDE dropout replication example (+0.170/+0.552/+1.449 vs.
+0.165/+0.601/+1.710, not itself a `tab:replication` row) and the
"three of four hold up... the fourth... is the retraction" interpretive
sentence, since neither restates a value already sitting in the table.
No further cut found within J5's specific scope (statistical
re-narration of table values) in §7 -- that section carries its own
unique 31%/78%/49-seed convergence numbers with no table to point to
instead, already compressed as far as M55b's own H4 sub-step took it.

### J6 — retired-recalibration paragraph in §8: COMPRESSED

Replaced the two-sentence recalibration-retirement explanation (which
also detailed "its anchors preserved, unmodified, as evidence of the
misdiagnosis, not deleted") with the milestone's own prescribed
one-sentence version, now pointing to the companion
paper~\cite{paper6-companion} (citation [11]) instead of leaving it
unremarked: "An earlier recalibration was retired once the floor fix
removed the collapse it had targeted; a companion paper in
preparation~\cite{paper6-companion} examines this and other live
evaluation-integrity findings from this rig in more depth." The
separate, unrelated E2-loop-feasibility sentence in the same paragraph
(citing `cacs26-paper`, one of the three standing fixed citations from
M54) was left untouched and un-merged, since it is a different,
standing finding that happens to share the paragraph, not part of "the
retired-recalibration paragraph" itself.

**Cut**: the "anchors preserved... not deleted" detail (prose only --
the actual retired data files remain untouched on disk per the
standing constraint, unaffected by this manuscript-text trim).
**Compressed**: the retirement explanation, now one sentence plus a
companion-paper pointer, as prescribed.

## Measured page count after each sub-step

| checkpoint | pages |
|---|---|
| GATE I (all three table fixes) | 23 |
| After J1 | 23 |
| After J2 | 23 |
| After J3 | 23 |
| After J4 | 23 |
| After J5 | 23 |
| After J6 | 23 |
| **Final (canonical 4-stage compile)** | **23** |

All six J sub-steps were used (none skipped for reaching 20 early,
since 20 was never reached). A direct pagination check
(`pdftotext`-based, tracking where Acknowledgements/Declarations/
References begin) shows real, non-cosmetic progress despite the
unchanged total: Acknowledgements and Declarations now begin on **page
20** (down from page 21 at the start of this gate), confirming the
body itself did shrink by close to a full page across J1-J6. The
References section still begins on page 21 and needs its own ~2.3
pages regardless, so total page count held at 23 -- the same
structural bottleneck M55b already identified and flagged.

## Zero-number-changed verification

Diffed every numeric token in `main.tex` before vs. after this gate
and traced every asymmetry by hand (same method as M55/M55b):

- **"Only added"** tokens (0.185, 0.205, 0.225, 0.245, 0.26, 0.28,
  0.30, 0.32, plus a couple of `\hspace` values): all are Group I's new
  `p{}` column-width fractions -- LaTeX formatting parameters, not
  data.
- **"Only removed"** tokens fall into two categories, both expected:
  (a) numbers belonging to a finding **explicitly authorized for full
  removal** this gate (0.99997/19.6/2.55 from J3; 0.0135/0.0053/
  0.0236/0.0059/0.23 from J4's removed paragraph; 0.03/1.44/the
  10$\times$ detail from J2 -- confirmed by direct grep that these
  specific values no longer appear anywhere, correctly, since their
  findings were cut, not merely reworded); (b) numbers that were
  restated in **two** places before and now only **one**, both
  confirmed present at least once by direct grep (0.0020, 0.084 --
  each had one instance in the now-cut spike sentence and a second,
  still-present instance in the retained churn paragraph/table; 1000,
  1009 -- still present multiple times elsewhere). No genuinely
  retained finding lost a number; every finding this gate cut lost all
  of its numbers together, consistently.
- Spot-checked the "1.44" and "0.03" tokens specifically (initially
  flagged) and confirmed both were false-positive substring matches
  (against "+1.449" and "+0.036"/"$p\leq0.03$" respectively, both
  unrelated retained numbers) -- FedProx's own 0.03%/1.44% values are
  genuinely and correctly gone, not accidentally surviving elsewhere.
- Confirmed all "do NOT cut" items remain present: the four safeguard
  findings (`tab:safeguards`'s 4 rows, unchanged), the churn retraction
  (both "opposite of immune" mentions intact), the 35.4% [25.5%,45.8%]
  scaling result (6 occurrences, all contexts checked), the
  deployability-vs-contention distinction (6 occurrences), the
  unit-mismatch standing finding ($-47.64$ still present), and the
  four bounded limits (Conclusion's "Four limits bound every claim in
  this paper" paragraph, unchanged).

**No headline number changed value; every cut finding's numbers are
legitimately and consistently gone.** Every retained figure still
matches its `docs/PAPER5_M49_reproducibility_manifest.csv` /
`docs/PAPER5_M54_claim_artifact_table.csv` row.

## Remaining overage and least-harmful next candidate

**23pp final, 3pp above the ~20pp target**, unchanged by this gate's
six real cuts. This independently reconfirms M55b's own diagnosis: the
body has now been compressed about as far as J1-J6 (plus M55/M55b's
own prior groups) can take it without touching a load-bearing finding,
and the **bibliography's fixed ~2.3-page footprint** (21 DOI-linked
entries) is the actual remaining constraint -- proven directly this
gate by the body shrinking a further ~1 page (Acknowledgements/
Declarations moved from page 21 to page 20) while the total held at 23
because References still needs pages 21-23 regardless.

**Least-harmful remaining candidate (not attempted, outside Groups
I/J as specified)**: tighten the bibliography's own typesetting --
e.g., a bare DOI string instead of the full `https://doi.org/...` URL
prefix on all 21 entries, or a more compact `\bibliographystyle` --
pure formatting economy that touches zero findings, numbers, or
manuscript prose, and is the same candidate M55b already flagged,
now with stronger evidence behind it (two independent gates' worth of
real body-content cuts that moved the body's own footprint but not the
bibliography-bound total).

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>  # no matches
grep -n "Overfull \\hbox" <final log>                        # no matches
```

Compiled and verified after Group I and after every J sub-step (J1-J6)
individually, and once more at the end as the canonical 4-stage
sequence. 23 pages, `main.pdf` regenerated, zero overfull-hbox
warnings anywhere in the document.

## STOP

Reported per the milestone's own gate. Final page count: **23** (table
overflow fully fixed; six authorized content cuts applied, verified
against the manifest/claim-to-artifact table; target ~20pp not
reached). Overage and the recommended, not-yet-authorized next
candidate (bibliography typesetting) reported above, per the gate's
own instruction not to cut a load-bearing finding to force the number.
Awaiting review before any further pass.
