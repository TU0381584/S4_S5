# M49b-4 — retirement of the `RealisticServedKpmSource` recalibration

## Status: NO RIG, write-up only. Closes the live-contamination arc's causal-mechanism question, established across M49b-1-1/2/3 (docs/PAPER5_M49b*, experiments/results/m49b_1/, m49b_2/, m49b_3/).

## 1. The recalibration's premise

`experiments/scripts/realistic_served_kpm_source.py` (built during the
original, pre-M41-fix M8/M27 work) replaces the offline environment's
synthetic served-capacity model with two hardcoded, UE-count-indexed
per-slice anchors:

```python
SERVED_PRB_3UE: Dict[str, float] = {"urllc": 5.0, "embb": 13.0, "mmtc": 5.0}
SERVED_PRB_6UE: Dict[str, float] = {"urllc": 10.0, "embb": 45.0, "mmtc": 10.0}
```

The manuscript's own §"Recalibrating the Simulator to Match Live
Congestion" states the reasoning behind this directly: a live
wide-open-ceiling sweep found "served PRB completely flat against
ratio for all three slices (urllc/mmtc at 5.00, eMBB at 13.00)," and
concluded from this that "the admission-ceiling lever... has no
measured effect on throughput at all," so the simulator should instead
"treat served capacity as a measured, ratio-independent constant" —
one that **doubles when UE count doubles** (5→10, 13→45, 5→10),
modelling a graded, UE-count-scaled capacity ceiling each slice
genuinely runs up against.

**This is the premise under test**: that each slice's served capacity
is a real, load-dependent constraint sitting near these specific raw-
PRB values, growing with UE count.

## 2. The evidence that falsifies it

`experiments/results/m49b_1/gate1_1_report.md` (M49b-1-1, live,
post-M41-fix, real 3UE/6UE composition — one UE per slice at 3UE, two
per slice at 6UE, including mmtc's genuine bursty 2s-on/6s-off
profile, not M44's own continuous-elevated substitute) measured, under
a deliberately wide-open ceiling so the reading reflects the
environment and not a policy:

| slice | 3UE served | 3UE offered | 6UE served (per UE) | 6UE offered (per UE) |
|---|---|---|---|---|
| embb | 3996.75 Kbps | 4000 Kbps (99.9%) | 3998.98 / 3998.75 Kbps | 4000 Kbps each (~99.97%) |
| urllc | 300.00 Kbps | 300 Kbps (100%) | 300.02 / 300.00 Kbps | 300 Kbps each (~100%) |
| mmtc | 13.39 Kbps | ~12.5 Kbps true average (~107%) | 13.12 / 13.12 Kbps | ~12.5 Kbps each (~105%) |

**All three slices serve essentially 100% of offered demand, with
0.000% loss, at both UE counts.** Combined with M44-A's and M44-E2b's
own already-published PRB-throughput calibration (embb's native 4 Mbps
demand is directly confirmed servable at exactly 5 raw PRB, 96.4%
clean, by a live pinned-ceiling test; urllc's and mmtc's native
demand, scaled from their own respective calibration curves, sits
close to or well under 1 raw PRB), the honest reading is:

**No slice's real demand approaches, let alone requires, a
graded/UE-count-doubling served-capacity ceiling anywhere near 5-45
raw PRB.** Real demand sits at or below the scheduler's own 5-PRB
floor at every load level this rig has ever tested it against. The
`SERVED_PRB_3UE`/`SERVED_PRB_6UE` anchors do not describe a real
physical constraint — they describe the exact signature of the M41
scheduler-floor bug (grants silently clamped near the observability
floor regardless of true demand), read as if it were genuine capacity
scarcity.

This closes the causal question `experiments/results/m44/gateA_report.md`
(M44-A) already flagged as a live methodological hazard but had not
yet connected back to the recalibration specifically: `avg_prbs_dl`
reading a flat value near the scheduler's minimum grant size is "not
because [that] PRB [count] is genuinely required" but because it is
"the finest granularity `avg_prbs_dl` can ever show." The original
live ceiling-sweep that motivated `RealisticServedKpmSource` read
exactly this artifact and treated it as a measured physical property.

## 3. Conclusion: the recalibration is retired

**`RealisticServedKpmSource` is retired.** It is not redesigned, not
re-run, and not deleted (per the standing constraint, it remains
untouched evidence — the exact contaminated anchors that motivated
this whole re-collection arc). Its own live "fix" — the manuscript's
own reported reversal of the 6-UE complete-collapse finding, taking
the recalibrated checkpoint live and finding "every episode blocked,
every block correctly targeting mmTC" — is now understood differently
than the manuscript currently states it: that live confirmation run
also predates the M41 fix (established in
`docs/PAPER5_M48b_provenance_audit.csv`), so the radio layer was still
structurally broken throughout it. The recalibration's live "fix" was
addressing the **floor bug's own symptom** (a checkpoint retrained
against fabricated scarcity happened to issue ceiling values that, by
coincidence of its own training distribution, sat in a band the
still-broken scheduler could still serve), not correcting a genuine
sim-to-real gap in offered demand. The floor bug is now fixed at its
actual root (M41, commit `cda9d65`) — every live gate in this arc
(M49b-1-1/2/3) confirms grants clear the floor with real native
traffic, no recalibrated checkpoint or fabricated anchor required.

**What this means for the manuscript** (for M54 to act on, not
executed here): the entire "Recalibrating the Simulator to Match Live
Congestion" subsection's causal story — collapse-was-OOD-extrapolation,
fixed-by-recalibration — is superseded by this arc's own finding
(collapse-was-the-floor-bug, fixed-by-M41). The subsection's
*empirical* observations (the original checkpoint's live behaviour
before and after the M41 fix, both now established directly by
M49b-2/M49b-3) remain real and reportable; its *interpretation* of
why does not survive.

## 4. Preserved, standing, separate finding: the SLA-margin unit-mismatch code bug

**This fix is unaffected by any of the above and stands on its own.**
The manuscript's diagnosis — that the margin computation divides a
per-slice backlog reading by a calibration constant tuned for the
offline environment's synthetic proxy, while live the identically-
named field is wired to the real MAC scheduler's transmit-buffer byte
count, two to three orders of magnitude larger in scale — is a real,
config-independent unit-conversion defect in how a diagnostic quantity
is computed and displayed. It is true regardless of whether the
underlying backlog value it's converting is large because of genuine
congestion or because of the floor bug's own starvation signature.

What M49b-2 (`experiments/results/m49b_2/gate_report.md`) revises is
only the **causal framing** the manuscript currently attaches to the
specific catastrophic case that motivated fixing it: it was described
as entering "a real, independently-documented backlog failure
regime," when in fact (per M49b-2's own re-derivation, native traffic,
post-fix: embb's margin lands at −47.64, ~21,000× smaller in magnitude
than the original −1,002,377.5, with the floor now clear throughout)
that specific catastrophic instance was very likely the floor bug's
own signature, not organic contention. The Little's-Law recalibration
formula itself — a physically meaningful byte-to-latency conversion
against each slice's own real latency budget — remains a correct,
useful fix to the unit-mismatch bug and should be kept in the
manuscript exactly as already written; only the one sentence
attributing the catastrophic case to "a real, independently-documented
backlog failure regime" needs revising in M54, to instead note that
the backlog level driving that specific reading is now understood to
be the pre-fix floor bug's own symptom.

## STOP

Reported per the milestone's own gate. Awaiting go before M49b-5
(offline re-grounding of M27's topology-scaling result).
