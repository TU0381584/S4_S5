# M49b-3 — GATE report: falsifying the pre-fix 3-vs-6-UE "collapse" claim, post-fix

## Pre-registered (given by the milestone spec, not decided here)

Prediction: the pre-fix 6UE "complete collapse to always-accept /
OOD generalisation failure" does NOT reproduce as a scarcity failure;
any 3UE-vs-6UE block-pattern difference post-fix is trained-bias/noise,
not OOD contention collapse. Escalate and report if 6UE surprisingly
still collapses with the floor cleared.

## Run

Exact M8 seed-900 `single_agent_dqn` checkpoint, `saclb_live.yaml`
(post-M41-fix, verified via `m42_floor_matrix`'s own parser before the
run: urllc/embb/mmtc all floor=6%→6 raw PRB, OK), cold-start,
contention gate PASS, **6UE native composition** (2 UEs/slice, real
bursty mmtc on both — reusing M49b-1-1's own second-UE bring-up and
M49b-2's own native-traffic xapp-invocation pattern, explicitly NOT
the elevated E4 regime M49b-2 caught and discarded — confirmed from
this run's own console line: "COLD START, 6UE NATIVE composition").
5 episodes in one continuous session, `eval_seed=3003`. Total elapsed
1518.4s (~25.3 min). Clean teardown.

**M41DBG scheduler-state confirmation**: 0 below-floor samples across
71,498 total readings, all three slices, across all 5 episodes (embb
mean max\_prbs=39.80, urllc=35.58, mmtc=35.20) — grants clear the
floor throughout, same as M49b-2's 3UE run.

## Per-episode results (all 5 episodes, seed 3003)

| ep | reward | blocks (all mmtc) | urllc compl. | embb compl. | mmtc compl. | all-slices compl. | urllc margin | embb margin | mmtc margin |
|---|---|---|---|---|---|---|---|---|---|
| 1 | −0.95 | 1 | 0.383 | 0.400 | 0.933 | 0.233 | −7.71 | −83.25 | +0.15 |
| 2 | −0.13 | 1 | 0.467 | 0.517 | 0.933 | 0.333 | −7.49 | −70.74 | +0.15 |
| 3 | +3.89 | 1 | 0.550 | 0.567 | 0.933 | 0.450 | −5.70 | −60.06 | +0.15 |
| 4 | +1.55 | 1 | 0.500 | 0.517 | 0.967 | 0.350 | −6.82 | −63.77 | +0.52 |
| 5 | +2.46 | 1 | 0.600 | 0.450 | 0.883 | 0.317 | −5.70 | −73.24 | −0.42 |
| **mean** | **+1.36** | **1.0** | **0.500** | **0.490** | **0.930** | **0.337** | **−6.68** | **−70.21** | **+0.11** |

**No episode shows anything resembling collapse-to-always-accept.**
Every single episode blocks exactly once, exclusively mmtc — the
identical qualitative pattern as M49b-2's 3UE run (mmtc-only, zero
urllc/embb blocks) and as M8's own original pre-fix report. No margin
anywhere near the pre-fix catastrophic scale (embb's worst episode,
−83.25, is ~12,000× smaller in magnitude than M8's own pre-fix
−1,002,377.5).

## Direct comparison: 3UE (M49b-2) vs 6UE (this gate)

| | 3UE (M49b-2, 1 episode) | 6UE (this gate, mean of 5) |
|---|---|---|
| blocks (all mmtc) | 27 | 1.0 |
| urllc margin | −2.13 | −6.68 |
| embb margin | −47.64 | −70.21 |
| mmtc margin | +0.81 | +0.11 |
| all-slices compliance | 0.517 | 0.337 |

6UE is mildly worse on margins and all-slices compliance than 3UE (as
real, if small, added load would predict — 2× the native UE count is
still, per M49b-1-1, far below the scheduler floor, but not literally
zero additional demand) — but this is a **quantitative shift within
the same regime**, not a qualitative collapse. Blocking is exclusively
mmtc-targeted at both loads (never urllc/embb), and — notably,
counter to a naive "more load → more blocking" story — the raw block
*count* is actually far lower at 6UE (1/episode) than 3UE's single
episode (27). This is reported as an observation, not a new claim
requiring further investigation (out of this gate's documented, not
campaign, scope): whatever triggers the policy's own mmtc-blocking
behaviour is not simply "more aggregate mmtc traffic," consistent with
it being a state-feature-driven trained bias rather than a
demand-reactive contention response.

## GATE M49b-3 verdict: CONFIRM(overturn), no surprise

The pre-fix 6UE "complete collapse to always-accept" **does not
reproduce**. Post-fix, 6UE's block pattern matches 3UE's own
trained-bias behaviour (mmtc-only, sparse, non-catastrophic), not an
out-of-distribution generalisation failure. No escalation triggered.

## The unified finding, established across three gates together

- **M49b-1-1** (environment): no real scarcity exists at either 3UE or
  6UE, native composition — all three slices' real demand sits at or
  below the 5-PRB scheduler floor.
- **M49b-2** (3UE, checkpoint): the catastrophic backlog runaway does
  not recur post-fix; the checkpoint still blocks only mmtc, but this
  blocking shows no evidence of protecting against real scarcity that
  M49b-1-1 already established doesn't exist.
- **M49b-3** (6UE, checkpoint, this gate): the pre-fix "6UE collapse"
  does not reproduce either; the same checkpoint shows the same
  qualitative mmtc-only-blocking pattern at 6UE as at 3UE, with no
  catastrophic margin anywhere.

**Together, these three gates establish that M8's original
"decision-transfer" and "3-vs-6-UE collapse" findings were both
readings of the same artifact — the pre-fix scheduler-floor bug — not
evidence of genuine contention-management competence or an
out-of-distribution generalisation failure.** The checkpoint's live
mmtc-blocking behaviour, observed consistently across both load levels
post-fix, is better characterised as the policy's own trained priority
bias (mmtc carries the lowest `priority_weight` by the reward's own
calibration, the same mechanism M2's own work already established)
executing in a contention vacuum, not admission control responding to
real load.

## Disk / cleanup

34G free before and after (raw gNB/UE console logs pruned after
extraction; omega log, xapp console log, and this report kept).

## STOP

Reported per the milestone's own gate. Awaiting go before M49b-4
(retire the recalibration, no rig) and M49b-5 (offline re-grounding of
M27).
