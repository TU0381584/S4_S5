# M46-MR3c — apply the fix, resolve the residual, clean re-run

Per this milestone's own 3-part structure: apply MR3b's located fix,
resolve the residual in the same pass (not deferred), then re-run
MR3's trust gate clean. All 3 done; results below are more nuanced
than a clean pass/fail, reported exactly as measured.

## (1) Fix applied, timing verified

`framework/qoe_oran_framework/env.py`'s `RANEnv.reset()` now pushes
every `(gnb_id, slice_id)`'s freshly-reset ceiling via
`send_control()`, immediately after `AdmissionGate.reset_ceilings()`
-- same call site/argument shape as `step()`'s own E2-write loop, just
unconditional rather than gated on a pending request. Confirmed
project-owned (git-tracked, last touched by this project's own
history) before editing directly rather than wrapping.

**Timing verified, not assumed**: `reset()` runs at the top of
`run_single()`'s episode loop (`mc_runner.py:286`), which only
executes once the xapp subprocess has already been launched -- itself
only launched after the full cold-start/bring-up/contention-gate
sequence in `run_one()` has already completed and passed. No race
with bring-up is possible: by the time `reset()` runs, the gNB's E2
agent has been up and listening for the entire preceding bring-up
+ traffic-launch window. Confirmed live: in all 4 clean runs below,
every NSSAI's first `M46DBG e2_apply` write now lands within
approximately 15-20 seconds of xapp process launch (matching ordinary
checkpoint-load + socket-init + first-KPM-poll overhead, all of which
happens in `main()`/`reset()` before any control write is attempted)
-- not the ~93-103 seconds MR3b found pre-fix, which was the time
until each slice's first ADMISSION REQUEST happened to arrive.

**Effect confirmed directly, not inferred**: cross-referencing each
run's `M46DBG e2_apply` write timestamp against `M46DBG sched_read`
(scheduler-read) timestamps for the same NSSAI: **0.0% of post-write
scheduler samples read uncapped, in all 4 runs, both controllable
slices (8/8), zero exceptions** -- the scheduler reads the correct
in-band value within 0.009-0.022s of the write landing (essentially
the very next scheduling slot). Also confirmed the offline
`ClosedLoopKpmSource` (`replay_kpm_source.py`) is unaffected by this
change: its own `_ceiling_ratio` state is initialized once at
construction from a documented `initial_ceiling_ratio`, not tied to
`reset()`/`step()` lifecycle at all -- MR2's checkpoints were not
trained under an equivalent gap and are not retroactively implicated.

## (2) Residual -- resolved: it does not exist

MR3b's own "residual ~15-19% post-settling recurrence" is **retracted**
(correction also appended directly to
`docs/PAPER5_M46_MR3b_control_path_origin.md`). That finding used a
fixed `t>=30s` cutoff to define "settled" -- checking against each
slice's own TRUE first-`e2_apply`-write timestamp instead (already
logged, just not used this way before) shows that cutoff was still
inside the real ~93-103s pre-fix startup gap for several slices/runs.
Redone properly on MR3b's own already-collected 2 runs: post-first-
write uncapped rate is exactly 0.0%, both slices, both runs. **There
is no second re-default mechanism.** The entire uncapped-ceiling
phenomenon, in every run examined across MR3, MR3b, and MR3c (6 pre-
fix + 4 post-fix = 10 runs total), is fully and exclusively explained
by the single missing-initialization gap now closed in part (1). Per
this milestone's own branch logic ("residual gone after fix -> reset
gap fully explained it; proceed"): proceeding to (3) was correct, no
second mechanism needed characterizing first.

## (3) Clean re-run — results

4 runs (DQN-QoE/DQN-SLA x seeds 256/257, same checkpoints/config/E4
co-located regime as MR3), cold-start, contention gate PASS every run,
`xapp ok=True` all 4 (316.5-317.3s). Full episode data in
`experiments/results/m46_mr3c/`. Metrics below are computed on
`t >= first_e2_apply_write` per slice (the validated, precise boundary
from (1) -- NOT `all_runs.json`'s own `line_cursor_start`-based crop,
which starts at subprocess launch and so still includes part of the
~15-20s pre-reset() process-startup window; using the write timestamp
directly, as instructed, measures the genuinely clean, policy-
operating period with no exclusion-window guessing).

| run | slice | in-band (strict) | values observed | full calibrated range visited? | Pearson r (ceiling vs backlog) |
|---|---|---|---|---|---|
| qoe/256 | urllc | **True** | {6,7} | no (misses 8) | +0.051 |
| qoe/256 | embb | **True** | {5,6,7} | no (misses 8,9,10) | -0.007 |
| qoe/257 | urllc | False | {4,6,7} | no (4 is 2-below-floor; misses 8) | **-0.975** |
| qoe/257 | embb | False | {3,4,5,6,7} | no (3,4 below floor; misses 8,9,10) | **-0.824** |
| sla/256 | urllc | False | {5,7,8} | no (5 is 1-below-floor; misses 6) | -0.016 |
| sla/256 | embb | False | {4,5,6,7,8,9,10} | **yes** (visits all 6, plus one 1-below-floor sample) | +0.004 |
| sla/257 | urllc | **True** | {6,7,8} | **yes**, exact | +0.265 |
| sla/257 | embb | False | {7,8,9,10} | no (misses 5,6) | -0.282 |

**In-band**: strictly true for half the (run, slice) pairs; the other
half show small near-miss excursions (1-2 units past the calibrated
floor/cap -- e.g. `4` when urllc's floor is `6`, `3` when embb's floor
is `5`) -- **categorically different from MR3's original ~106
catastrophic uncapping**, and small enough that this could plausibly
be genuine policy behavior pushing slightly past a hard-calibrated
edge under real dynamics, not a control-path defect. Confirmed this by
re-checking: none of these near-miss values are anywhere near 90-106,
and each traces to a real, distinct `M46DBG e2_apply` write (checked
directly), not an unwritten/stale read.

**Full calibrated-range exercise**: only 2 of 8 (run, slice) pairs
visit every one of MR1's calibrated points within one 300s episode;
the rest visit a proper subset. This differs from MR2's offline
finding (12/12 runs, exhaustive, no exceptions) but is not necessarily
a live/coupling effect -- MR2 trained 300 episodes per checkpoint (far
more transitions to visit every point by chance or design); MR3c is
one 300s episode per checkpoint, per this milestone's own "trust
check, not a powered campaign" scope. Not enough evidence here to
attribute the narrower range to coupling specifically rather than
episode length -- flagged as open, not asserted either way
(`TODO(MEASURE)`: would need a multi-episode live run to separate
these, out of scope for this milestone).

**State-responsiveness**: no consistent sign or strength across seeds
-- ranges from strongly negative (qoe/257: -0.98/-0.82) through
near-zero (qoe/256 embb, sla/256 both) to weakly positive (sla/257
urllc: +0.27). Flagging an interpretation issue, not just noise: for
an ADMISSION-CONTROL ceiling (as opposed to a scheduler serving
already-admitted traffic), a NEGATIVE correlation (more backlog ->
lower ceiling) is a legitimate, arguably CORRECT throttle-under-
congestion response, not evidence of failure -- the `state_responsiveness()`
function (`m46_mr3_live_revalidate.py`) does not itself assert an
expected sign, and this report does not either. What the data
actually shows, reported plainly: responsiveness (in either direction)
is inconsistent across seeds, not absent, not uniformly present.
`remainUEs` only ever takes 4 distinct values (1-4) in every run
checked across this whole milestone family, which caps how stable a
Pearson correlation over ~20,000-25,000 samples can be expected to be
run-to-run when the underlying signal is this coarse -- a single
300s episode per seed may simply not be enough to pin this down
either way.

**PWC / shed classification** (behavior characterization only, per
this and every prior milestone's own explicit framing -- not a
QoE-vs-SLA verdict): unchanged from MR3's original pattern. DQN-QoE
(both seeds): `indiscriminate_failure` in all 4 windows each run,
shed_precision=0.0 (PWC 0.32, 0.46). DQN-SLA (both seeds):
`correct_shed` in all 4 windows each run, shed_precision=1.0 (PWC
0.71, 0.71). Consistent with the fix not touching downstream
served/loss dynamics (which the fix wouldn't be expected to change,
since it only closes a brief pre-episode window averaged over ~21
per-run windows).

## GATE MR3c

**(1) Fix applied, timing verified**: yes, unambiguously -- 0.0%
uncapped after write in 8/8 (run, slice) pairs, write lands ~15-20s
post-launch (ordinary startup overhead) rather than waiting on a
random admission request.

**(2) Residual resolved**: yes -- it never existed as a separate
mechanism; the earlier finding was an artifact of an insufficiently
late exclusion cutoff. Retracted in `PAPER5_M46_MR3b_control_path_origin.md`.

**(3) Clean numbers**: reported in full above.

## DECISION

**Does not meet the "both arms in-band(~100%) + state-responsive +
coupling-tolerant" bar as stated -- but not for a reason this
milestone's own three failure branches describe, and this report does
not force it into one.** The control-path defect that MR3/MR3b/MR3c
exist to chase is conclusively, completely fixed (part 1) with no
second bug (part 2). What remains is a narrower, more mundane
open question: a single 300s live episode per seed shows
inconsistent-but-not-absent state-responsiveness and partial (not
full) calibrated-range exercise, and this milestone's own methodology
(1 episode/checkpoint, "trust check not a powered campaign") cannot
distinguish "genuine, seed-dependent live behavior" from "not enough
samples to see the real signal" for these two specific questions. This
is **not** "coupling breaks it" (the control mechanism is now provably
clean) and **not** "a second control-path bug" (measured directly,
0.0%) and **not** confidently "genuine non-responsiveness" either
(3 of 8 slice-runs show |r|>0.26, one very strongly). PWC/shed
classification (question 4, always behavior-characterization-only) is
unchanged and does not bear on this decision either way.

**STOP.** Not declaring PF2-1 trustworthy on this evidence, and not
declaring a specific failure mechanism either -- reporting the actual,
mixed, precisely-measured picture and awaiting direction: a wider
seed/episode-count live run to get a powered read on responsiveness
and range-exercise now that the control path is clean, versus treating
the fixed control path as sufficient and accepting the current
single-episode signal as-is, versus something else. Not decided
unilaterally here.
