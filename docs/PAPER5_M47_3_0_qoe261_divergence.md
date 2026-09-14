# M47-3-0 — characterizing qoe/261's divergence (NO RIG)

M47-2-3 found qoe/seed261 is the only QoE checkpoint (1 of 12
live-tested) that classifies `correct_shed` rather than
`indiscriminate_failure` -- 0.0% urllc loss, ceilings near cap for
both slices across the whole live episode, matching the SLA arm's own
"leave ceilings open, let the scheduler protect urllc" signature
exactly, despite being trained under the QoE reward. Before this
becomes one row in PF2-1c's powered matrix, this gate asks whether
it's an EXPLICABLE training-path divergence (a mechanism-confirming
case study) or a SEED-LOTTERY outcome (inexplicable from training
data -- QoE failure is probabilistic, not deterministic).

## Method

Compared all 12 QoE seeds' OFFLINE training trajectories (already
collected by MR2/M47-2-1, no new computation of new quantities, no
new live time) across every signal available:

1. Reward curve (Q1/Q4 mean, per-episode), from
   `experiments/results/m46_mr2/convergence_report.csv` +
   `experiments/results/m47_2_1/convergence_report.csv`.
2. Loss curve (Q1/Q4 mean, by train_step call order), same source.
3. Final epsilon (decay-schedule sanity check), same source.
4. Full in-band action-range exercise (already established 12/12,
   MR2 + M47-2-1), same source.
5. **New for this gate**: the OFFLINE ceiling-position/reject-
   intensity pattern across the full 300-episode training run --
   same normalized-`[0,1]`-within-`[floor,cap]` method PF2-1b used on
   LIVE data, applied here to each seed's own
   `omega_log.jsonl` (`evidence.ceilings`, every training step, all
   300 episodes) -- both the whole-run mean and the LAST QUARTILE
   specifically (the tail of training, closest to what the frozen
   checkpoint actually does), since a checkpoint's live behavior
   should track what it converged TO, not its whole training history
   equally.

## Result: seed 261 is unremarkable by every offline signal checked

| seed | reward Q1->Q4 | loss growth% | urllc reject-intensity (whole/last-Q) | embb reject-intensity (whole/last-Q) |
|---|---|---|---|---|
| 256 | -0.079 | 246.1% | 0.225 / 0.119 | 0.519 / 0.634 |
| 257 | -0.089 | 285.8% | 0.252 / 0.132 | 0.481 / 0.536 |
| 258 | -0.080 | 222.9% | 0.215 / 0.104 | 0.551 / 0.623 |
| 259 | -0.078 | 120.5% | 0.202 / 0.084 | 0.555 / 0.618 |
| 260 | -0.058 | 127.9% | 0.215 / 0.106 | 0.556 / 0.637 |
| **261** | **-0.058** | **141.9%** | **0.182 / 0.088** | **0.662 / 0.601** |
| 262 | -0.032 | 109.6% | 0.233 / 0.113 | 0.568 / 0.713 |
| 263 | -0.116 | 413.3% | 0.261 / 0.099 | 0.603 / 0.702 |
| 264 | -0.068 | 118.6% | 0.223 / 0.148 | 0.647 / 0.683 |
| 265 | -0.175 | 449.1% | 0.242 / 0.099 | 0.464 / 0.659 |
| 266 | -0.044 | 91.7% | 0.242 / 0.171 | 0.494 / 0.557 |
| 267 | -0.047 | 173.1% | 0.201 / 0.112 | 0.543 / 0.579 |

(Final epsilon: 0.050 in all 12, no exception. Full in-band action
range: {6,7,8}/{5,6,7,8,9,10} exact in all 12, no exception -- omitted
from the table since there is no variation to compare.)

**Seed 261 sits squarely inside the range of the other 11 on every
column.** Reward Q1->Q4 (-0.058) is tied with seed 260, nowhere near
an outlier (range across all 12: -0.032 to -0.175). Loss growth
(141.9%) sits mid-pack (range: 91.7% to 449.1%). Its offline ceiling-
position pattern -- both the whole-run mean AND specifically the
LAST-QUARTILE view (closest to what the frozen checkpoint converged
to) -- is unremarkable too: urllc reject-intensity 0.182 (whole-run)
is the lowest of the 12, but not by a discriminating margin (259 is
0.202, 267 is 0.201 -- a smooth distribution, not a gap); embb's
0.662 (whole-run) is the highest of the 12, but again not
discontinuously so (264 is 0.647, 263 is 0.603). **No single metric,
and no combination of these metrics, marks seed 261 as visibly
different from the other 11 during offline training.**

## Interpretation: SEED-LOTTERY, not an explicable case study

Checked every offline signal this project's own established
convergence-check methodology provides, plus a new, finer-grained
ceiling-position analysis specifically designed to catch a subtler
divergence than the coarse "visited the full range" boolean already
known to be identical across all 12 -- **none of it distinguishes
seed 261 from the other 11 QoE checkpoints.** This is not a case of
"we didn't look hard enough" -- reward, loss, epsilon, action-range,
and ceiling-position (both aggregate and end-of-training) all agree:
by every measure available from the offline training process itself,
qoe/261 is an unremarkable member of its cohort. Its live divergence
only manifests once deployed against real, live, E4-coupled radio
dynamics that `ClosedLoopKpmSource`'s offline training environment
cannot represent (Path B's own known, documented scope limit -- the
same "offline convergence predicts nothing about live behavior" claim
Stage 12 established for offline-vs-live comparisons in aggregate,
now shown to hold at the level of individual seed variance WITHIN one
reward arm, not just between arms or between offline/live means).

**This is SEED-LOTTERY: QoE's live failure mode is probabilistic
(~11/12, 92% at this sample size), not a deterministic property of
the QoE reward that every seed reliably reproduces.** The paper's
framing must say "the QoE reward fails to protect urllc in the large
majority of trained instances at this regime" -- not "the QoE reward
always fails" or "necessarily fails." One in twelve independently-
seeded, offline-identical-looking training runs landed in a
qualitatively different, SLA-like live behavioral basin, for reasons
this milestone's own offline instrumentation cannot see.

## Update to PF2-1c's framing

Per this gate's own instruction, carried forward explicitly rather
than left implicit: **the DQN split entering PF2-1c is 11/12 QoE
`indiscriminate_failure` (a strong, probabilistic effect) and 12/12
SLA `correct_shed`, not a deterministic property of either reward.**
qoe/261 is included in the QoE arm's pooled checkpoints as-is for
PF2-1c -- its divergence is data characterizing the arm's own
variance, not a case for exclusion.

## GATE M47-3-0

**Divergence characterization**: complete, across reward, loss,
epsilon, action-range, and offline ceiling-position (whole-run and
last-quartile) -- no explanatory signal found in any of them.
**Interpretation: SEED-LOTTERY** (probabilistic, ~92% QoE failure
rate at n=12), not an explicable training-path case study. PF2-1c's
own framing updated accordingly, above.

## STOP

Characterization complete, interpretation settled (seed-lottery).
Awaiting go before PF2-1c.
