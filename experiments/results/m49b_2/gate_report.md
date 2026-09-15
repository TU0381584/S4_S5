# M49b-2 — GATE report: falsifying the M8 decision-transfer-under-load claim, post-fix

## Pre-registered (given by the milestone spec, not decided here)

Prediction = OVERTURN. CONFIRM(overturn) = post-fix, blocks no longer
track a scarcity signal / accepted+rejected requests both fully served.
SURPRISE = genuine differentiated shedding still appears (escalate).

## A real execution mistake, caught and corrected before drawing any conclusion

First attempt (eval_seed=3001) reused `m46_mr3_live_revalidate.run_one()`
unmodified. Its own console output line — `COLD START
urllc=3600Kbps/12x embb=12000Kbps/3x mmtc=native` — revealed that
function hardcodes the elevated E4 co-located regime built for the
M45-M47 characterization work, not M8's own native-traffic composition.
Confirmed by reading the source directly (`run_one()`'s own
`URLLC_MULT`/`EMBB_MULT` overrides, applied unconditionally after an
initial native gate-phase). This is precisely the wrong test for this
milestone's own question (whether the NATIVE-load claim survives), so
that run's data is discarded and NOT used for this gate's conclusion
(preserved, clearly labeled, at
`experiments/results/m49b_2/DISCARDED_wrong_traffic_level_e4_regime_sla/`).
A new function, `run_native_m8_style()`, mirrors `run_one()`'s own
cold-start/gate/xapp/teardown structure exactly but keeps native (1.0x)
traffic for the entire run — the corrected run below used this.

## The corrected run

Config verified to clear the 5-PRB floor before the run (reusing
`m42_floor_matrix`'s own already-validated parser, itself fixed this
same gate after an ad-hoc regex version mis-attributed one slice's
match to a stray code comment — safety-check correctness matters):
urllc/embb/mmtc all report floor=6% → 6 raw PRB, OK. Checkpoint: the
exact M8 seed-900 `single_agent_dqn` checkpoint. Config:
`saclb_live.yaml` (post-M41-fix). Cold-start, contention gate PASS,
native traffic for all 3 slices throughout, 1 episode (~314s),
`eval_seed=3002`.

**M41DBG scheduler-state confirmation**: 0 below-floor samples across
35,702 total M41DBG readings, all three slices, for the entire run
(embb mean max\_prbs=52.77, urllc=49.07, mmtc=43.36) — grants clear the
floor for accepted requests throughout, unlike the pre-fix run which
could not.

## Result 1 — the backlog/margin causal story: clean CONFIRM(overturn)

| | pre-fix (M8's own report) | this run (post-fix, native) |
|---|---|---|
| embb SLA margin | +1.0 → **−1,002,377.5** (catastrophic) | **−47.64** |
| urllc SLA margin | (not separately reported pre-fix) | −2.13 |
| mmtc SLA margin | (not separately reported pre-fix) | **+0.81** (healthy) |

The catastrophic backlog runaway **does not recur** post-fix at native
load — embb's margin is ~21,000× smaller in magnitude than the
original catastrophic reading, and mmtc's margin is positive
(healthy). The unit-mismatch CODE bug itself is unchanged (these
numbers are still on the old, wrong-scale units the milestone
correctly said stands independent of this test) — what changed is
whether the *underlying real backlog* ever reaches the regime that
made the mismatch look catastrophic, and post-fix, at native load, it
does not. This directly confirms the CONTEXT's own suspicion: the
"real, independently-documented backlog failure regime" M8's own
report invoked to explain the catastrophic case was the floor bug's
own signature, not organic contention.

## Result 2 — the block-pattern claim: neither a clean CONFIRM nor a clean SURPRISE

Blocks this run: **27, all mmtc, zero urllc, zero embb** — the
identical qualitative pattern M8's own pre-fix report described ("Both
live runs blocked only mMTC... zero urllc or eMBB blocks in either").
Compliance: urllc 76.7%, embb 60.0%, **mmtc 98.3%** (its blocking
target), all-slices 51.7%.

Read superficially, 27 non-zero blocks looks like it could trigger the
SURPRISE branch ("genuine differentiated shedding still appears"). But
per M49b-1-1's own finding (all three slices' real native demand sits
at or below the 5-PRB floor, fully servable regardless of ceiling),
mmtc's own real demand at this load would almost certainly have been
served just as well if none of these 27 requests had been blocked —
its margin is already healthy (+0.81) and its compliance already near-
ceiling (98.3%) *with* the blocking in place. **The blocking pattern
persists, but there is no evidence it is protecting mmtc from any real
scarcity, since M49b-1-1 already showed there is none to protect
against at this load.** This reads as the policy exercising its own
trained bias (mmtc carries the lowest `priority_weight` by the
reward's own calibration, per M2's own already-established mechanism)
independent of live contention, not as contention management that
happens to still be necessary.

**This is reported as a third, precise finding, not force-fit into
either pre-registered box**: the causal STORY behind the original
claim (differentiated shedding as evidence of live contention
management) is overturned, but the surface-level BEHAVIOR (mmtc gets
blocked, others don't) is unchanged. Whether this distinction matters
enough to warrant the SURPRISE escalation (a fuller campaign
characterizing why the policy still blocks mmtc when nothing forces
it to) is a call for the user, not decided here.

## Disk / cleanup

34G free before and after (raw gNB/UE console logs for both the
discarded and corrected runs pruned after extraction; omega logs,
xapp console logs, and this report kept).

## STOP

Reported per the milestone's own gate. Awaiting go before M49b-3.
