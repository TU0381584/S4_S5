# M49b manuscript changelog

Every change to `Papers_4-5/Paper_5/WPC/main.tex` made under the M49b
milestone, in order. Per the standing "changelog every manuscript
change" constraint — this file is appended to, not overwritten, as
later M49b sub-gates make further edits.

## M49b-0 (2026-09-15, no rig)

1. **Added two new macros** (`\prefixflag`, `\prefixinline`) near the
   existing `\authorTODO` definition, for marking content under live
   re-collection without deleting it.
2. **Abstract**: appended an inline flag to the live-single-gNB-anchor
   sentence ("A live single-gNB anchor confirms the architecture's
   decision logic transfers to real traffic unchanged.").
3. **Introduction, paragraph 1**: rewrote the first `cacs26-paper`
   citation. Dropped "showing its compliance advantage survives
   correction for multiple comparisons where an SLA-only reward's does
   not" (unsafe per `docs/PAPER5_M48b_citation_sweep.csv` — cites
   Paper #4's compliance headline, which M43-P0/M42 found the metric
   is structurally blind to and the config structurally below the
   scheduler floor). Replaced with the permitted facts: E2 control
   loop feasibility and median round-trip latency (0.57ms), for a
   policy under 20,000 parameters.
4. **Introduction, closing paragraph**: appended an inline flag to the
   "offline-trained decision logic transfers to live traffic
   unchanged" sentence.
5. **§"Live Single-gNB Anchor"**: added a section-level flag box
   immediately after the section header, naming the exact config
   commits (82b20f6, 40ae2f3) and fix commit (cda9d65) and pointing to
   the provenance audit.
6. **§"Heavier Live Load"**: added a section-level flag box after the
   subsection header, naming the specific alternative explanation
   (floor-starvation universal failure signature vs. genuine OOD
   generalisation failure) this section's finding must be checked
   against.
7. **§"Recalibrating the Simulator to Match Live Congestion"**: added a
   section-level flag box after the subsection header, naming the
   specific premise now in question (the "served PRB flat against
   ratio" reading is very likely the `avg_prbs_dl` observability-floor
   artifact M44-A later documented, not a real property of the control
   surface).
8. **§"Cluster-Size Scaling" (results-m27), closing paragraph**:
   rewrote the second `cacs26-paper` citation. Dropped "independently
   confirms the same offline-to-live transfer for a QoE-aware reward
   variant on the same rig, at 128 episodes per arm with correction for
   multiple comparisons" and the trailing "two independent live
   campaigns" framing sentence (both leaned on the now-flagged claim);
   kept the E2-latency/parameter-count fact. Added an inline flag to
   the preceding sentence about this section's own live anchor.
9. **Conclusion**: rewrote the third `cacs26-paper` citation. Dropped
   "a QoE-aware reward's compliance advantage surviving correction for
   multiple comparisons"; kept "well-behaved for a single gNB,
   negligible round-trip latency, a lightweight policy."

**Net effect**: 0 numbers changed, 0 claims deleted. 3 citations to
Paper #4 rewritten to drop the one now-unsafe clause from each while
preserving every fact the binding citation rule still permits. 5 flags
added marking exactly which of WPC's own claims are pending
re-collection, each naming the specific re-verification question at
stake rather than a generic "TBD."

**Verification**: `pdflatex` + `bibtex` + `pdflatex` ×2 from a clean
`.aux`/`.bbl` state, exit code 0 throughout, 26 pages (was 25 before
this change — expected, from the added flag text), zero undefined
references or citations. Pre-existing cosmetic warnings (duplicate
hyperref destination names, one bookmark-depth warning) are unchanged
from before this edit and not introduced by it.

## STOP

GATE M49b-0 complete. Awaiting go before any M49b live rig work
(M49b-1 onward).
