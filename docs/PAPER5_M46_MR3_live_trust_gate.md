# M46-MR3 — THE TRUST GATE: live revalidation of MR2's retrained checkpoints

## CORRECTION (2026-09-11, from M46-MR3b)

**Question (1) below overstates severity and question (2)'s
correlations are understated.** M46-MR3b's diagnosis of the uncapped-
ceiling origin found that the ~31-37%-of-samples figure reported below
is a real count of logged M41DBG lines, but a misleading measure of
real-world/wall-clock impact: M41DBG logging is rate-limited to
~1-in-20 scheduler calls, and the scheduler's own call rate is far
from time-uniform, running disproportionately densely during the
volatile first ~15-30s after traffic launch. Re-reading this report's
own already-computed per-window `trajectory` data (not re-collected --
the same `results/m46_mr3/*/trajectory.jsonl` written at the time)
shows the uncapped ceiling is concentrated almost entirely in the
episode's first 15-30 seconds, then clean and stable for the remaining
~90%+ of wall-clock time, in all 4 runs. Root cause (confirmed via new
live pointer-identity instrumentation): `RANEnv.reset()` never pushes
the post-`reset_ceilings()` starting ceiling to the gNB via
`send_control()` -- the real applied ceiling for a slice sits at the
gNB's own boot default until that slice's first admission request is
processed, independent of anything coupling-related. Recomputed
state-responsiveness on the settled (t>=30s) samples: urllc
r=0.65-0.85 (not 0.18-0.44), embb r=0.51-0.73 (not the originally
reported near-null -0.05 to +0.19) -- the startup-gap block of points
was diluting a substantially stronger live-backlog-tracking
relationship for both slices. Question (3)'s "does not transfer"
framing and the DECISION below should be read alongside this
correction, not taken at face value; question (4)'s PWC/shed
classification did not depend on this and is not reopened. Full
account: `docs/PAPER5_M46_MR3b_control_path_origin.md`.

Live, cold-start, running the REAL policy control loop
(`framework/qoe_oran_framework/xapp/saclb_xapp.py`, frozen, unmodified)
against the real gNB/E2, at E4's co-located regime (urllc 3600Kbps/12x +
embb 12000Kbps/3x, mmtc native). 4 runs: DQN-QoE and DQN-SLA, 2 seeds
each (256, 257 — the same checkpoints MR2 produced), 1 episode/run
(~300s), matched on reward-mode only, per this milestone's own "trust
check, not a powered campaign" scope. Every run: fresh docker-core +
native-stack cycle, contention gate, identical cold-start discipline to
every prior M44/M45 live milestone. Never touched `min_rbSize`/
`tx_maxsize`/frozen source; never widened the action space (same MR1
config, unedited, for every run).

## Run provenance

| run | mode | train seed | eval seed | checkpoint | elapsed | xapp exit |
|---|---|---|---|---|---|---|
| 1 | qoe | 256 | 950 | `m46_mr2/offline_train/qoe/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt` | 317.1s | ok |
| 2 | qoe | 257 | 951 | `m46_mr2/offline_train/qoe/seed257/dqn/offline_closed_loop/rep_0/checkpoint.pt` | 318.3s | ok |
| 3 | sla | 256 | 952 | `m46_mr2/offline_train/sla/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt` | 317.7s | ok |
| 4 | sla | 257 | 953 | `m46_mr2/offline_train/sla/seed257/dqn/offline_closed_loop/rep_0/checkpoint.pt` | 317.7s | ok |

All 4 contention gates PASSED before their run. Full per-run results:
`experiments/results/m46_mr3/all_runs.json`; raw trajectories, omega
logs, xapp/traffic console logs: `experiments/results/m46_mr3/`.

Runs 1-2 executed 2026-09-08 00:46-01:06 local; run 3 (sla/256) was
mid-episode when a disk-full condition on the host crashed the `mongo`
core container (unrelated to this script — see incident note below);
the entire sweep was discarded and re-run cleanly end-to-end after the
environment was verified healthy (git fsck clean, all MR2 checkpoints/
omega logs re-verified loadable, mongo restarted with confirmed subscriber-data
integrity). All 4 runs reported here are from that clean re-run
(2026-09-08 01:45-02:08 and 11:42-12:01, split by an operator-requested
overnight pause taken cleanly after run 2's live episode completed and
its trajectory data was confirmed written, with a full live-stack
teardown in between — no run was interrupted mid-episode).

## GATE MR3 answers

### (1) Does the live-commanded ceiling stay in MR1's calibrated band?

**No — same clean pass/fail question MR2 asked offline, now failing
live, in all 4 runs.** `EXPECTED_RANGE` (urllc {6,7,8}, embb {5-10} raw
PRBs) comes from MR1's own single-slice static calibration
(`config_band_alignment.csv`), calibrated at the SAME per-slice offered
loads MR3 uses (urllc 3600Kbps/12x, embb 12000Kbps/3x) — so this is not
a load mismatch. `urllc_in_band`/`embb_in_band` are `False` for every
run because the M41DBG `ceiling` line's `max_prbs` (the scheduler's
ACTUAL computed PRB grant for that slice that slot — confirmed
mechanistically by M44-E2b: an unconstrained slice reads near the cell's
full `n_rb_sched_init`, ≈106) periodically jumps far outside the
calibrated band, up to the full ≈106.

Re-parsing the raw M41DBG stream (not preserved in the summary JSON) to
characterize this precisely rather than just report the boolean:

| run | slice | n samples | in-band (%) | ≥95 "uncapped-looking" (%) | dominant in-band value(s) |
|---|---|---|---|---|---|
| qoe/256 | urllc | 37507 | 64.9% | 35.0% | 6 only (never 7 or 8) |
| qoe/256 | embb | 37507 | 64.9% | 34.8% | 5 (dominant), 6 (rare) |
| qoe/257 | urllc | 37269 | 64.7% | 35.2% | 6 only |
| qoe/257 | embb | 37269 | 63.2% | 36.5% | 5 (dominant) |
| sla/256 | urllc | 32116 | 54.4% | 33.0% | 8 (dominant), 5 (rare) |
| sla/256 | embb | 32116 | 61.5% | 33.1% | 10 (dominant), 7 (rare) |
| sla/257 | urllc | 36904 | 55.8% | 31.6% | 8 (dominant), 5, 7 |
| sla/257 | embb | 36904 | 63.8% | 31.6% | 10 (dominant), 7, 8 |

**The pattern is bimodal, not exploratory:** almost nothing between the
in-band value(s) and ≈95-106 (the qoe arm's urllc, for example, is
*exactly* 6 every single in-band sample across both seeds — it never
once visits 7 or 8, the other two MR1-calibrated points). This is the
opposite of MR2's offline finding that both arms exercise the full
`{6,7,8}`/`{5,6,7,8,9,10}` range in all 12 runs, no exceptions.

**Checked whether the ≥95 samples are benign** (i.e., the slice's buffer
was momentarily empty, so no cap needed to be enforced that slot — a
real, validated scheduler idiom per M44-E2b). They are not: cross-
referencing each ≥95 ceiling sample against the same-slot `postpf`
`remainUEs` value, **100% of the ≥95 samples, every run, every slice,
occur while `remainUEs` is 1-4 (real pending backlog)**. The ceiling is
reading fully uncapped roughly a third of the time while UEs are
actually waiting to be scheduled — a genuine, load-bearing control lapse
under live conditions, not a parsing artifact or a benign idle-buffer
reading.

### (2) Does the live ceiling actually track live backlog state?

**Weak-to-moderate for urllc, essentially absent for embb** — Pearson r
between commanded `max_prbs` and same-slot `postpf remainUEs`, native
M41DBG sample granularity (not the coarser 15s PWC window, which would
wash out exactly this relationship):

| run | urllc r (lag0 / lag5) | embb r (lag0 / lag5) | n |
|---|---|---|---|
| qoe/256 | 0.399 / 0.395 | -0.005 / -0.036 | ~24,000 |
| qoe/257 | 0.344 / 0.342 | 0.094 / 0.075 | ~24,000 |
| sla/256 | 0.392 / 0.439 | 0.053 / -0.007 | ~19,800 |
| sla/257 | 0.177 / 0.172 | 0.194 / 0.151 | ~23,500 |

`remainUEs` only ever takes values 1-4 across every run (a narrow
range by construction of this traffic pattern), which caps how large
any correlation here could plausibly be. Given the bimodal in-
band/uncapped structure found in (1), the urllc correlation is most
plausibly explained by the coarse bound-vs-released switching loosely
tracking backlog magnitude, not by graded modulation within the
calibrated band (which barely gets visited at more than one point, per
above). embb shows no meaningful state-tracking in either lag.

### (3) Does MR2's offline behavior (full action-range exercise, clean env) transfer to the live, E4-coupled regime?

**No.** MR2 answered its own gate-2 question ("does each policy exercise
its full in-band range?") with an unambiguous, exception-free pass:
12/12 offline runs visit every calibrated point,
`{6,7,8}`/`{5,6,7,8,9,10}`/`{5}`, exactly. Live, under E4's real
cross-slice contention (the coupling `ClosedLoopKpmSource` structurally
cannot represent — the exact confound PF2-0 flagged and MR2 explicitly
left open), the SAME checkpoints instead show: (a) collapse to one or
two static in-band points rather than the full calibrated range, and
(b) a genuine ~31-37%-of-the-time uncapped excursion with real backlog
present, never observed or even possible to observe offline. This is
the coupling confound manifesting concretely, not a hypothetical: the
offline-verified "exercises its full range, not a static ceiling"
finding — the exact criterion MR2's own gate treated as decisive — does
not hold once real multi-slice coupling is introduced.

### (4) PWC / PWC_eq / shed classification — behavior characterization, NOT a QoE-vs-SLA verdict

Reused unmodified from `m45_priority_weighted_correctness.py`
(`C_k(t) = clip(served/offered,0,1) * (1 - rlc_reject_frac)`,
`Score(t)` weighted `w_urllc=5.0`/`w_embb=3.5` for PWC, equal-weighted
for PWC_eq, 15s windows matching M44's convention):

| run | PWC | PWC_eq | mean C_urllc | mean C_embb | shed classification (4/4 windows) | shed precision | urllc failures |
|---|---|---|---|---|---|---|---|
| qoe/256 | 0.432 | 0.379 | 0.674 | 0.084 | `indiscriminate_failure` ×4 | 0.0 | 4/4 |
| qoe/257 | 0.438 | 0.386 | 0.681 | 0.092 | `indiscriminate_failure` ×4 | 0.0 | 4/4 |
| sla/256 | 0.567 | 0.514 | 0.815 | 0.213 | `correct_shed` ×4 | 1.0 | 0/4 |
| sla/257 | 0.706 | 0.643 | 1.000 | 0.286 | `correct_shed` ×4 | 1.0 | 0/4 |

Consistent with the raw served/loss trajectories (`all_runs.json` →
`trajectory`): both DQN-QoE runs sacrifice embb heavily (loss settles
≈72-73%) while urllc STILL degrades (loss climbs to ≈20-23% in later
windows) — embb's sacrifice "buys nothing," the exact
`indiscriminate_failure` definition. Both DQN-SLA runs also sacrifice
embb heavily (loss settles ≈47-56%) but keep urllc's loss at ≈0%
throughout — the exact `correct_shed` definition.

**This is reported as a real, seed-consistent (2/2 in each arm)
behavioral difference under this one live overload regime — nothing
more.** Per this milestone's own explicit framing (identical to MR2's):
n=2 seeds/arm, 1 episode/run, one specific co-located regime is not a
powered comparison and this is NOT a claim that DQN-SLA "wins" or is
more trustworthy in general. Critically, **both arms independently fail
gate questions (1)-(3) above in the same way** (bimodal in-band/uncapped
ceiling behavior, no clean range exercise) — the shed-classification
split describes what each policy's live actions produced downstream,
not that either policy's underlying live ceiling control is sound.

## What this does NOT establish

Not a claim that `saclb_xapp.py`, the E2 interface, or the gNB
scheduler are broken in general — M44-E2b already mechanistically
validated the same M41DBG ceiling/`max_prbs` pipeline against a
single-slice, non-adaptive ceiling and found it binds correctly there.
What MR3 adds is that under an ADAPTIVE policy issuing live, changing
ceiling commands against genuinely coupled multi-slice contention, the
resulting `max_prbs` behavior does not match what MR1's static,
single-slice calibration predicted — consistent with, but not
mechanistically dissected down to, the specific scheduler code path
that produces this (out of scope for this milestone; a natural next
static-source-reading follow-up if this needs isolating further). Not a
QoE-vs-SLA verdict (per (4) above). Not a claim about any other traffic
regime, config, or algorithm family — scope is exactly MR1's Path A
config, DQN, this one E4 co-located point.

## Incident note (environment, not methodology)

During the FIRST attempt at this sweep (discarded), a host disk-full
condition (root filesystem hit 100%, traced to a 24GB swap file plus
accumulated logs) starved multiple system processes, including a real
crash of the `mongo` docker container (ENOSPC on its FTDC diagnostic
writer). Swap was reduced to 8GB, stale logs/caches/an old kernel
package were cleaned, mongo was restarted (WiredTiger journal replay
recovered cleanly in 153ms) and its subscriber data was confirmed
intact (count=9, matching every prior healthy bring-up this project has
recorded) before this sweep was re-run from scratch. No git corruption,
no MR1/MR2 artifact loss. Reported for completeness; unrelated to the
GATE MR3 findings above, which come entirely from the clean re-run.

## DECISION: STOP (see correction above -- the "coupling-breaks-it" basis for this is weaker than stated; re-evaluate against MR3b before acting on it as originally worded)

Per this milestone's own decision structure: **trustworthy → PF2-1**,
**in-band-not-responsive → STOP**, **coupling-breaks-it → STOP**. The
evidence above spans both STOP conditions rather than fitting one
cleanly — embb shows in-band-collapse with no meaningful
responsiveness (question 2), and both slices show the offline full-
range-exercise finding failing to transfer under real coupling
(question 3), with a genuine, backlog-present ceiling-uncapping
behavior offline testing could not have surfaced. Reported honestly as
a mixed but unambiguous STOP rather than forced into a single label.
PF2-1 should not proceed on these checkpoints/config as-is. Awaiting
go on how to proceed (e.g., isolating the scheduler-side mechanism
behind the uncapped excursions, or a Path A retrain that includes
cross-slice coupling in the training env — out of scope to decide
unilaterally here).
