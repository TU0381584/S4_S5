# M57 — restructure per author requests (23pp → 21pp; target 20pp, 1pp short)

## Status: NO RIG, complete (LaTeX-only). Target: `Papers_4-5/Paper_5/WPC/main.tex` @ M56's `0ff94a2`. Compiles clean at every stage and at the final canonical sequence (pdflatex → bibtex → pdflatex ×2, exit 0 every stage, zero undefined references or citations, zero overfull-hbox warnings). **Final page count: 21pp**, down from 23pp, 1pp short of the ~20pp target.

## Final section structure (measured, not estimated)

```
1 Introduction
2 Related Work
3 System Model and Problem Formulation
4 GAT-CTDE Method
  4.1 Shared Encoder, Decentralised Q-Heads   (now also carries the training-collapse diagnosis)
  4.2 Federated Training with Differential Privacy
  4.3 Experimental Setup
  4.4 Evaluation Safeguards                   (merged in from the old standalone §5)
5 Results                                     (merged from the old §6 Multi-gNB Results, §7 Cluster-Size Scaling, §8 Live Deployment, §9 Cluster-Size N=7)
  5.1 Centralised
  5.2 Federated Training and DP
  5.3 Disruption
  5.4 Cluster-Size Scaling                    (N=19 and N=7 folded into one flowing subsection)
  5.5 Live Deployment
6 Conclusion
```

**Numbering note, reported transparently**: the milestone's own text named the merged Results section "§6" and said "Conclusion becomes §7." A section-by-section count of the CONTEXT's own described surgery (delete §5 as a standalone section, merge four sections into one) puts Results at natural position 5 and Conclusion at 6, which is what LaTeX's automatic `\section`/`\subsection` numbering actually produces here (confirmed above, not asserted). No manual re-numbering, `\setcounter` trick, or artificial extra section was introduced to force the literal "6"/"7" labels — that would have meant either leaving a stray empty section or inserting a not-requested one. The requested STRUCTURE (limits condensed, §5 merged into §4, §6-9 condensed into one results section, Conclusion immediately after) is implemented exactly as described; only the specific numerals in the milestone's own prose don't match a plain recount, flagged here rather than silently reconciled.

## Measured page count per group

| checkpoint | pages |
|---|---|
| Starting point (M56's `0ff94a2`) | 23 |
| After Group A | 22 |
| After Group B | 22 |
| After Group C (main merge) | 21 |
| After Group C (extra: disruption-mechanics de-dup) | 21 |
| **Final (canonical 4-stage compile)** | **21** |

## Group A — brief limitations + de-emphasise insignificant bug detail

- **Compressed** (not cut) the Conclusion's four-limits paragraph from ~34 lines to 3 sentences, each limit named once: offline-only multi-gNB scope, the disclosed-harder-than-live stress regime, no MEC/compute-placement nodes in the graph, and the synthetic single-operator FL privacy setting. Kept both companion citations (`cacs26-paper`, `paper6-companion`) and the closing "stand independently of it" clause.
- **Removed** the redundant restatement of the offline-only/no-live-multi-gNB-test limit from the Live Deployment section's own intro (it duplicated System Model's own canonical statement of the same limit); replaced with a cross-reference (`Section~\ref{sec:system-model}`).
- **Compressed** (not cut) the append-mode log-contamination finding to one sentence: the bug existed, was caught, logs cleared, no retraining needed. Dropped the episode-index-reset detection detail and the save-routine-isolation verification detail (neither is a manifest-tracked number).
- **Compressed** (not cut) the unit-mismatch SLA-margin defect to one sentence naming it as a standing finding plus the Little's-Law fix. **Dropped the $-47.64$/$-1{,}002{,}377.5$ internals** per the milestone's own explicit authorization ("UNLESS the number is load-bearing elsewhere (it is not)") -- confirmed by grep before removal that these values appeared nowhere else in the manuscript and are not cited in the Introduction, Conclusion, or any table.
- **Left untouched**: the scheduler-floor cross-layer integrity finding, at full finding-level detail, exactly as instructed.

**Measured effect: −1pp** (23→22).

## Group B — merge §5 Evaluation Safeguards into §4, remove Fig. 2

- **Moved** the training-collapse diagnosis (the privacy-sweep discovery, the Q-value-probe confirmation, the magnitude-encoding causal mechanism, and the two-fixes/collapse-count result) out of the old standalone §5 and **integrated it into §4.1** as the empirical motivation for the `LayerNorm` + per-slice-Q-head design choices already described there -- stated once, failure→fix→result, immediately followed by the pre-existing theoretical (shared-parameter/class-imbalance) explanation for why per-slice heads specifically help. Added a `LayerNorm` mention to §4.1's own architecture-description sentence, since it is now a permanent part of the described design, not just a "fix" introduced later.
- **Removed Fig. 2** (`fig2_collapse_reduction.pdf`) entirely, including its `\caption`/`\label`. Its content (the 0/30→3/30→21/30 differentiate-count progression across the unnormalised encoder, the `LayerNorm`-only fix, and the per-slice-head fix) is now carried as one clause inside the merged §4.1 paragraph, exactly as specified. Confirmed via `grep -n "ref{fig:collapse}"`: **zero remaining references** after the edit (the compiler's own zero-undefined-references check independently confirms this).
- **Renamed** `\section{Evaluation Safeguards}` to `\subsection{Evaluation Safeguards}`, positioned (already, by construction) immediately after `\subsection{Experimental Setup}` -- no section reordering needed, only the header level changed. Kept `\label{sec:collapse}` on this subsection (all of its own existing cross-references still resolve; LaTeX renumbers automatically).
- **Re-pointed four cross-references** that specifically meant "the collapse-diagnosis methodology" (in the Introduction, System Model, the M3/federated section, and the N=19 scaling section) from `\ref{sec:collapse}` to `\ref{sec:methodology-perslice}`, since that content moved. **Left one cross-reference unchanged** (the M2 results table's own footnote, "Low compliance is the metric artifact Section~\ref{sec:collapse} explains") since it refers to the correctness-metrics *explanation* of why compliance drops, which stayed in the (now-merged) Evaluation Safeguards subsection.
- The 44/49 (89.8%)/21/24 (87.5%) metric-disagreement result and the reproduction-vs-replication discipline paragraph **moved into the merged 4.4 subsection unchanged**, with only their own internal self-reference ("the one collapse diagnosed above" → "...diagnosed in Section~\ref{sec:methodology-perslice}") updated to point at the new location.

**Measured effect: 0pp** (22→22; real, sub-page savings from removing Fig. 2's own float overhead, but no boundary crossed on its own).

**GATE B confirmation**: `grep -n "fig:collapse\|fig2_collapse"` returns zero matches; compile log shows zero undefined references.

## Group C — condense §6-§9 into one Results section, Conclusion follows

- Renamed `\section{Multi-gNB Results: Centralised, Federated, and Disruption}` → `\section{Results}`, and its three subsections to `Centralised`, `Federated Training and DP`, `Disruption` (shorter titles, same content and labels).
- **Cut** (not compressed) one sentence from the Centralised subsection that had become a direct, exact duplicate of Group B's own new §4.1 content ("21 of the 30 seeds show genuine, correctly-targeted differentiated shedding, up from 3/30... and 0/30 originally") -- replaced with a two-word cross-reference, since restating the identical progression twice in the same paper is pure redundancy Group B's own merge created.
- **Converted** `\section{Cluster-Size Scaling}` to `\subsection{Cluster-Size Scaling}` in place, and **relocated** the entire `\section{Cluster-Size Scaling at $N{=}7$}` block (previously positioned *after* Live Deployment) to immediately follow the $N{=}19$ content within the same subsection, ahead of Live Deployment -- this is a genuine content **move**, not a copy: the old section header and its now-duplicate location were deleted after the content was relocated and lightly re-flowed (removing now-redundant `\S\ref{sec:results-m6}` self-references that read oddly once both scales share one subsection, e.g. "matching \S\ref{sec:results-m6}'s own primary identity" → "the same primary identity as above"). `\label{sec:results-m27}` and `\label{tab:m27-n7}` moved with their content and still resolve correctly (confirmed: zero undefined references after the move).
- Renamed `\section{Live Single-gNB Deployment}` → `\subsection{Live Deployment}` in place (already immediately following Cluster-Size Scaling once the $N{=}7$ block was relocated ahead of it -- no further move needed).
- **Extra compression** (beyond the minimum merge): the Disruption subsection's dropout/spike/churn mechanics were defined twice in adjacent paragraphs (once as a bulleted definition, once again as "Each disruption kind intercepts the frozen policy's per-step evaluation loop differently..."); merged into one paragraph carrying the union of both descriptions, cutting the second paragraph entirely. This was the "least-harmful remaining prose" identified after the main merge left the page count 1pp short of target -- pure mechanism-description de-duplication, no finding, number, or caveat touched.
- Every other table/figure re-narration in this region (`tab:m2-results`, `tab:disruption`, `tab:replication`, `tab:m27-n7`) was already condensed as far as M55/M55b/M56's own prior groups took it; no further safe cut was found there without touching a preserved finding or a number not already covered by an adjacent table.

**Measured effect: −1pp from the main merge** (22→21), **0pp from the extra disruption-mechanics de-dup** (21→21, real but sub-page savings, did not cross a further boundary).

## Zero-number-changed verification

Diffed every numeric token in `main.tex` before vs. after this milestone and traced every asymmetry:

- **"Only added": none.** No new numeric token appears anywhere in the diff that wasn't already in the document -- this milestone moved and cut content, it introduced no new figures of any kind (not even formatting parameters, since Group A/B/C touched no tables' column specs).
- **"Only removed"**: every instance traces to one of two authorized categories: (a) the unit-mismatch defect's internal numbers ($-47.64$, $-1{,}002{,}377.5$, tokenized by the diff as "47.64", "377.5", "1", "002"), explicitly authorized for removal in Group A and confirmed by direct grep to be fully and consistently gone (**0 occurrences**, not orphaned partially); (b) numbers that were **stated twice before and now once**, confirmed present at least once by direct grep: the 0/30→3/30→21/30→9/30 collapse-count progression (Group B's merge consolidated two statements of the same numbers into one; each individual value -- 0/30, 3/30, 9/30, 21/30, 27/30 -- is still present exactly where the single canonical statement now lives, in §4.1 and in `tab:safeguards`).
- Spot-checked every item on the milestone's own PRESERVE list and confirmed all present: the four `tab:safeguards` rows (training collapse, eval-log contamination, reproducibility gap, scheduler-floor bug), the 44/49 (89.8%) and 21/24 (87.5%) metric-disagreement result, the churn retraction (present in Related Work, the Disruption subsection body, and the Conclusion -- three separate mentions, all intact), the 35.4% [25.5%,45.8%] scaling result (6 occurrences across the document, all contexts checked), the deployability-vs-contention distinction (6 occurrences), and the scheduler-floor cross-layer integrity finding (6 occurrences of "cross-layer").

**No headline number changed value; every cut item's numbers are the specific internals explicitly authorized for removal, fully and consistently gone. Every preserved finding remains intact**, matching `docs/PAPER5_M49_reproducibility_manifest.csv` and `docs/PAPER5_M54_claim_artifact_table.csv`.

## Remaining 1pp: structural, not prose

The gap is small (1pp) and, on inspection, is the same structural bottleneck flagged at every condensation gate since M55b: the paper's body content (Introduction through Conclusion) now occupies within 19 pages, and the bibliography's own 21 DOI-linked entries occupy a genuinely full 2 pages on their own (page 21 alone holds 11 dense, DOI-bearing entries with no slack) -- confirmed directly this time by inspecting the actual rendered page 21, not inferred. Closing this last page through further prose compression would require cutting content deep enough to risk a preserved finding, which this gate's own instruction explicitly forbids; the one additional safe cut available (the disruption-mechanics duplication) was found and applied, and no comparable safe candidate remains in the merged Results section without re-opening the same preserved-finding numbers already checked above.

**Least-harmful remaining candidate (not attempted, outside this milestone's three groups)**: the same one flagged at M55b and M56 -- bibliography typesetting economy (bare DOI strings instead of full `https://doi.org/...` URLs, or a more compact `\bibliographystyle`). This is pure reference-list formatting, touches zero manuscript prose, findings, or numbers, and would very plausibly close the remaining 1pp on its own given page 21 is entirely bibliography.

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>  # no matches
grep -n "Overfull \\hbox" <final log>                        # no matches
```

Compiled and verified after Group A, Group B (with the explicit fig:collapse/old-§5 dangling-reference check), and Group C (main merge + the extra de-dup step), and once more at the end as the canonical 4-stage sequence. 21 pages, `main.pdf` regenerated, every `\ref`/`\label` pair resolving (confirmed both by the compiler's own "no undefined references" pass and by manual grep-based tracing of every relocated label).

## STOP

Reported per the milestone's own gate. Final page count: **21** (down from 23pp; target ~20pp, 1pp short). Restructuring implemented exactly as requested (limits briefed, §5 merged into §4 with Fig. 2 removed, §6-§9 condensed into one Results section with Conclusion immediately following); the section-numbering discrepancy in the milestone's own prose ("§6"/"§7") vs. the natural auto-numbered outcome ("§5"/"§6") is flagged above for confirmation, not silently resolved either way. Remaining 1pp gap is structural (bibliography length), with the same not-yet-authorized fix flagged as at every prior gate. Awaiting review before any further pass.
