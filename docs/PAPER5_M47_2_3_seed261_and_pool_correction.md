# M47-2-3 — gate seed 261, reach 12/arm margin — and a real correction to the "22/22 deterministic" assumption

Seed 261 was already trained by MR2's original run (256-261, confirmed
via `experiments/results/m46_mr2/convergence_report.csv`: both arms
completed 300/300 episodes, full in-band action-range exercised) --
no new training needed, went straight to the live trust-gate using
M47-2-2's identical pre-committed criteria (in-band: 0 samples
`max_prbs>=90` in the clean window, both slices; responsiveness:
Pearson r computable, both slices; coupling: contention gate PASS +
`ok=True`), same script (`experiments/scripts/m47_2_2_trust_gate_one.py`,
extended only to add seed 261's eval_seed mapping -- no criteria
change).

## Result: both PASS -- but qoe/261 is a real, confirmed exception to the prior pattern

| mode | seed | in_band | responsiveness | coupling | overall | shed classification |
|---|---|---|---|---|---|---|
| qoe | 261 | PASS | PASS | PASS | **PASS** | **correct_shed** |
| sla | 261 | PASS | PASS | PASS | **PASS** | correct_shed |

sla/261 matches the established SLA pattern exactly (12/12 SLA
checkpoints now `correct_shed`, zero exceptions). **qoe/261 does
NOT** -- it is the first QoE checkpoint, out of 12 now live-tested,
to classify `correct_shed` rather than `indiscriminate_failure`.

**Verified this is real, not a computation artifact**, by checking the
underlying per-window served/loss data directly (not just trusting the
classification label): at the same trajectory window (window 10,
150-165s), all 6 OTHER new QoE seeds show substantial urllc loss
(22.3-44.8%, matching `indiscriminate_failure`'s signature -- urllc
still fails despite embb being sacrificed) while **qoe/261 shows
exactly 0.0% urllc loss** -- urllc fully protected, matching SLA's own
signature precisely, with embb still sacrificed (49.1% loss, in the
same range as every other run). qoe/261's ceiling behavior also
matches: `urllc_m41dbg_maxprbs_mean` ~7-7.6 (near its cap of 8) and
`embb_m41dbg_maxprbs_mean` ~9.6 (near its cap of 10) across the whole
episode -- the same "leave both ceilings open, let the scheduler
protect urllc" mechanism PF2-1b's decomposition found explains SLA's
success, appearing here in a QoE-trained checkpoint.

**This is a real, seed-dependent training outcome, not noise**: this
specific seed's offline training run apparently converged to a
different region of policy behavior than the other 11 QoE checkpoints
tested to date (which all converge to the heavy-both-slices-throttling
behavior PF2-1b characterized as self-defeating). Nothing about the
trust-gate criteria, the live regime, or the analysis pipeline differs
for this checkpoint -- same config, same protocol, same instrumentation
-- the difference is in what the checkpoint itself learned.

## Correction to this milestone's own incoming framing

The context this milestone opened with stated the shed-split as
"22/22 deterministic on committed draws." **That was accurate through
M47-2-2 (22/22: 11 QoE `indiscriminate_failure` + 11 SLA
`correct_shed`) but is no longer accurate at 24/24** (12+12): the
correct count is now **11/12 QoE `indiscriminate_failure` + 1/12 QoE
`correct_shed`, and 12/12 SLA `correct_shed`**. PF2-1c's own incoming
instructions characterize the DQN split as "an already-22/22-
deterministic effect... not the campaign's novel content" -- this
milestone finds that framing needs updating before PF2-1c proceeds:
the QoE arm is NOT perfectly deterministic across seeds, and PF2-1c's
own primary-draw QoE-arm result should be read as a sample from an
arm with at least one confirmed outlier in its own trustworthy pool,
not as a foregone conclusion. This does not change PF2-1c's own scope
(the three-way static-arm comparison and the independent-draw
replication remain the real open questions) but it does mean PF2-1c's
own report should not describe the QoE-vs-SLA split as fully settled
going in -- 11/12 is strong, not unanimous.

## Trustworthy pool, final

| arm | live-validated & PASS | trained but never live-tested | total trained |
|---|---|---|---|
| DQN-QoE | **12** (all of 256-267) | 0 | 12 |
| DQN-SLA | **12** (all of 256-267) | 0 | 12 |

Every trained checkpoint in both arms is now live-validated. 12/arm
gives one checkpoint of margin above the n=11 very-conservative power
bar (M47-1), so a replication-time exclusion (if PF2-1c's independent
draw disqualifies any single checkpoint for a criteria-relevant
reason) cannot drop the headline pool below n=11.

## GATE M47-2-3

**261 PASS/FAIL per arm**: both PASS. **Resulting pool size: 12/arm**,
target met. **Flagged, not smoothed over**: qoe/261's `correct_shed`
classification is a genuine, verified exception to the pattern every
other QoE checkpoint has shown -- corrects the "22/22 deterministic"
framing to 23/24 (11/12 QoE + 12/12 SLA), and this correction is
carried into PF2-1c's own analysis below rather than left implicit.

## STOP

Pool at 12/arm, margin secured. Awaiting go before PF2-1c.
