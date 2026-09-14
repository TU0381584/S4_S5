# M45-PF2-1b — reject-mechanism decomposition + pre-registration lock

NO RIG. Decomposes the stable shed-classification split (DQN-SLA
`correct_shed` / DQN-QoE `indiscriminate_failure`, unchanged across
MR3, MR3c, and PF2-1a -- 14/14 run-arm instances, zero exceptions) into
its admission-layer and serve-layer components, to determine what
PWC/shed-classification actually measures before pre-registering it as
PF2-1c's hypothesis. Full data:
`experiments/scripts/m45_pf21b_reject_decomposition.py`,
`experiments/results/m45_pf21/pf21b/manifest.csv` (28 run-slice rows,
MR3's 4 original runs + MR3c's 4 + PF2-1a's 6, no new live time).

## Method

**Reject-intensity**: where a slice's commanded ceiling (`M41DBG`
`max_ratio`) sits within its own calibrated `[floor, cap]` band,
normalized to `[0,1]` (0 = always at floor, 1 = always at cap).
Grounded directly in `AdmissionGate.apply()`
(`action_mapping.py`): `max_ratio` only ever moves within
`[min_ratio_floor, max_ratio_cap]` in `step_ratio` increments -- a
mean position near floor is a direct, mechanical trace of mostly-
reject decisions; near cap, mostly-accept. Filtered to
`floor<=max_ratio<=cap` before averaging (not a time-based cutoff) --
any sample outside that range is unambiguously not a real accept/
reject decision (MR3b/MR4 already established this), which correctly
excludes MR3's original boot-default contamination without needing
MR3c's precise write-timestamp instrumentation MR3 predates.

**Serve-through**: `mean_c_urllc`/`mean_c_embb`, reused unmodified from
`m45_priority_weighted_correctness.py`'s own `C_k(t) = clip(served/
offered,0,1) * (1-rlc_reject_frac)` -- real, downstream, radio-layer
delivered traffic, already computed per run, not re-derived here.

## Result: NOT differential rejection targeting -- a different, decomposable mechanism

| arm | slice | reject-intensity (mean, 14 runs) | serve-through (mean) |
|---|---|---|---|
| DQN-QoE | urllc | **~0.00** (13/14 runs; one outlier, see below) | 0.44-0.72 |
| DQN-QoE | embb | **~0.00-0.02** (13/14 runs; one outlier) | 0.06-0.19 |
| DQN-SLA | urllc | **~0.97-1.00** (14/14) | 0.77-1.00 |
| DQN-SLA | embb | **~0.96-0.99** (14/14) | 0.21-0.29 |

**The task's proposed hypothesis -- "SLA rejects embb harder / QoE
rejects urllc harder, same protect-by-reject mechanism, different
target" -- is NOT what the data shows.** There is no differential
targeting WITHIN either arm: DQN-SLA keeps BOTH slices' ceilings open
(near cap, minimal rejection of either); DQN-QoE keeps BOTH slices'
ceilings closed (near floor, heavy rejection of both). The arms differ
in OVERALL throttling posture (SLA: permissive; QoE: restrictive),
applied near-uniformly across both controllable slices within each
arm, not in which specific slice each arm singles out.

**What actually explains the split, decomposed by mechanism:**

1. **DQN-SLA's `correct_shed` is a serve-side outcome, not an
   admission-side one.** urllc's ceiling stays open (~1.0) AND its
   serve-through is near-perfect (0.77-1.00) -- consistent. But
   embb's ceiling is ALSO open (~0.96-0.99, essentially as unthrottled
   as urllc's) while its serve-through stays low (0.21-0.29) --
   **embb is not being denied admission; it is losing real scheduler-
   level PRB contention against the higher-priority slice despite an
   open ceiling.** This matches this project's own long-established
   finding (M44-D/E2b and the M41 envelope-sweep family) that urllc's
   smaller, spectrally-cheaper packets and higher configured priority
   win real PF-scheduler contention on their own, independent of
   admission-layer intervention. SLA's "protection" of urllc costs it
   nothing at the admission layer -- it doesn't need to throttle
   anyone, because the scheduler already favors urllc once both
   ceilings are left open.

2. **DQN-QoE's `indiscriminate_failure` is a genuine admission-side
   defect, and it is self-defeating, not targeted.** Both slices are
   throttled near-floor -- this is NOT "protect urllc by rejecting
   embb"; it's "reject almost everyone, regardless of slice." embb's
   serve-through (0.06-0.19) is, if anything, WORSE than under SLA
   despite ALSO being heavily throttled at admission -- throttling
   embb's ceiling did not help it, consistent with (1)'s finding that
   embb's fate is set at the scheduler, not the admission gate. urllc's
   OWN serve-through under QoE (0.44-0.72) is markedly WORSE than
   under SLA (0.77-1.00) **despite urllc facing the identical real
   scheduler-contention advantage in both arms** -- the only
   difference is that QoE's own heavy-handed admission throttling of
   urllc's OWN requests caps how much urllc traffic ever reaches the
   scheduler to compete in the first place. **QoE's near-floor urllc
   ceiling is not protecting urllc -- it is constraining it below what
   the real radio conditions would otherwise let it achieve.**

**Net**: the shed split is real (confirmed independently by this
decomposition, not just replicated by the same PWC number), but it is
not a story about which slice gets targeted for rejection -- it is a
story about overall throttling posture (SLA permissive / QoE
restrictive) interacting with where the REAL bottleneck actually lives
(the scheduler, for embb; QoE's own admission gate, for urllc). PWC/
shed-classification, as a metric, is measuring this whole combined
admission+scheduler outcome, not admission-layer behavior alone -- important
to state plainly before it gets pre-registered as "the" test.

**One flagged exception, not smoothed over**: PF2-1a qoe/259's embb
reject-intensity is 0.948 -- starkly different from every other
DQN-QoE embb observation (0.00-0.02, 13/14 runs). Every other metric
for that run (serve-through 0.195, shed classification still
`indiscriminate_failure`) is unremarkable and consistent with the rest
of the QoE arm. `TODO(MEASURE)`: not investigated further this
milestone (no new live time in scope); flagged as a single-run
anomaly in an otherwise 13/14-consistent pattern, not asserted as a
second mode of QoE behavior.

## Pre-registration: written separately, committed alongside this report

Per this milestone's own explicit instruction -- do not pre-register
the per-slice directional sign (PF2-1a already observed it; pre-
registering it now would be postdiction, not prediction) -- the
formal pre-registration document is
`docs/PAPER5_M45_PF21_preregistration.md`, committed in the same
commit as this report. It pre-registers ONLY the still-untested claim
(the 4-arm shed-classification split at power, on a fresh eval draw)
and documents the per-slice signs and this reject-mechanism finding as
CHARACTERIZATION, not hypothesis.

## The power fork -- stated for supervisor decision, not resolved here

PF2-1a's power calculation (paired on PWC, n=5, d=3.52 raw / 1.76
conservative / 0.88 very-conservative) found required n of 1 / 3 / 11
respectively. **11 (the "very conservative," still only a
conventionally-"large" effect-size assumption) exceeds the entire
6-seed checkpoint pool MR2 produced (256-261) -- there is no way to
reach that bar without training new seeds, which is out of scope for
this NO-RIG milestone and a real time/compute cost decision.**

**Fork, not resolved here**:
- **(a) Run n=6** (all of MR2's existing seeds, one -- 261 -- still
  untested live): clears the "conservative" bar (n=3) comfortably,
  falls short of "very conservative" (n=11) by design. The
  pre-registration document states this explicitly as
  underpowered-by-its-own-most-conservative-standard, not hidden.
- **(b) Train more seeds first**: reaches genuine power by this
  milestone's own conservative bar, at the cost of new offline
  training time (out of scope to schedule here) before any further
  live time is spent.

Stated here for Pang/Phang's decision, per the milestone's own
instruction -- not decided unilaterally.

## GATE PF2-1b

**(1) Differential rejection targeting or serve-side component?**
Neither cleanly -- decomposed above: SLA's success is serve-side
(scheduler naturally favors urllc once both ceilings are left open);
QoE's failure is a genuine but UNTARGETED admission-side defect
(throttles both slices similarly, hurting urllc's own serve-through in
the process without protecting embb, whose fate is set at the
scheduler regardless).

**(2) Pre-registration**: committed, `docs/PAPER5_M45_PF21_preregistration.md`
-- shed-classification split only, per-slice signs as characterization.

**(3) Power fork**: stated above, explicitly for supervisor decision.

**STOP. Awaiting go — the campaign does not launch until the power fork is decided.**
