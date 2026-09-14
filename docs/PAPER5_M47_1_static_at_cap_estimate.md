# M47-1 — does static-at-cap reproduce DQN-SLA? (NO RIG estimate)

Before spending any offline-training or live-rig time extending the
checkpoint pool, this milestone first asks whether the powered
campaign's whole premise (DQN-SLA vs DQN-QoE as the primary
comparison) still makes sense given PF2-1b's own decomposition
(`docs/PAPER5_M45_PF21b_reject_decomposition.md`): DQN-SLA "protects"
urllc only by leaving both slices' ceilings wide open and letting the
real scheduler do the work -- which is exactly what a non-learning
static-at-cap arm would do too, by construction.

## Method

Reused PF2-1b's own reject-intensity data
(`experiments/results/m45_pf21/pf21b/manifest.csv`, no new
computation, no new live time) and went one level finer: instead of
the normalized `[0,1]` mean position within `[floor,cap]`, counted
what fraction of each DQN-SLA run's valid (`floor<=max_ratio<=cap`)
samples sit at the EXACT cap value -- the literal, discrete question
"is this indistinguishable from a policy that never leaves cap,"
not just "is it close to cap on average" (a run that alternated
evenly between floor and cap could average out to the same `[0,1]`
position as a run that sits at cap 95% of the time, and only the
per-value distribution tells them apart).

## Result: DQN-SLA has converged to (near-)literal static-at-cap, both slices, every run

All 7 DQN-SLA runs examined (MR3's 2 original + MR3c's 2 + PF2-1a's 3,
zero cherry-picking -- every DQN-SLA run collected across this
project's M46/M45 family to date):

| era | seed | urllc: % samples at exact cap (8) | embb: % samples at exact cap (10) | urllc ever at floor (6)? | embb ever at floor (5)? |
|---|---|---|---|---|---|
| MR3 | 256 | 100.00% | 96.12% | no | no |
| MR3 | 257 | 95.98% | 89.30% | yes (314/23535, 1.3%) | no |
| MR3c | 256 | 99.99% | 94.71% | no | no |
| MR3c | 257 | 96.06% | 89.52% | yes (317/24332, 1.3%) | no |
| PF2-1a | 258 | 99.99% | 95.15% | no | no |
| PF2-1a | 259 | 100.00% | 97.36% | no | no |
| PF2-1a | 260 | 94.51% | 93.16% | yes (275/20117, 1.4%) | no |

**urllc**: 94.5-100.0% of samples at the exact calibrated cap, every
run. The only deviations are brief dips to 6 or 7 (never more than
~1.4% of samples at the literal floor, in 3 of 7 runs) -- consistent
with occasional, isolated reject decisions, not a sustained
alternative policy. **embb**: 89.3-97.4% at exact cap, every run,
**never once at its own floor (5) in any of the 7 runs** -- the small
remainder sits at 7, 8, or 9 (one-to-three units below cap), not at
the bottom of the band.

**Estimate, stated plainly**: a literal static-at-cap policy (the
config below) would differ from what DQN-SLA has actually been doing,
live, across every run collected, by roughly 3-11% of samples for
embb and 0-5.5% for urllc -- and those differing samples are
themselves clustered near cap, not at the opposite extreme. The
downstream outcome (serve-through, shed-classification) is a function
of the real scheduler's response to the ceiling trajectory it's
handed; a trajectory that's 90-100% identical to constant-cap should
produce a very similar outcome, though this is an inference from the
ceiling data, not a live-confirmed equivalence -- that confirmation is
exactly what running the static-at-cap arm live (PF2-1c) provides,
and this estimate is not a substitute for it.

## GATE M47-1 verdict

**static-at-cap ≈ DQN-SLA.** DQN-SLA has converged to a policy that
is behaviorally near-indistinguishable from "always accept, ceiling
pinned at cap" for both controllable slices, in every run examined,
with no exceptions and no seed-dependent variation in this
conclusion (the 7-run range is tight: 94.5-100% urllc, 89.3-97.4%
embb -- no run comes remotely close to exercising the floor-to-cap
range the way MR2's OFFLINE training data (300 episodes/checkpoint)
did).

**Per this milestone's own branch logic: the primary hypothesis
becomes three-way**: static-at-cap ≈ DQN-SLA > DQN-QoE -- i.e., the
pre-registered claim is no longer just "SLA protects urllc where QoE
doesn't," but "learned admission control does not beat a trivial
non-adaptive policy, and the QoE reward's learned behavior actively
makes things worse." This is still untested at power (no run has yet
compared static-at-cap's REAL live outcome against DQN-SLA's on the
same regime) and is honestly pre-registrable as a fresh claim, unlike
the per-slice sign PF2-1a already observed.

**`docs/PAPER5_M45_PF21_preregistration.md` updated accordingly** (see
that file's own revision) -- primary claim restated as the three-way
comparison; the original two-arm DQN-SLA-vs-DQN-QoE claim is kept as a
secondary/component comparison within it, not discarded.

## Config built

`experiments/configs/m47/saclb_m47_static_at_cap.yaml` -- built on
M46-MR1's corrected `saclb_m46_train.yaml` (NOT the pre-fix
`saclb_campaign_static_at_cap_v2.yaml`, which would silently
reintroduce the exact below-scheduler-floor bug M41/M42 fixed). Same
mechanism as Paper #4's own established static-at-cap arm:
`nominal_ratio` raised to equal `max_ratio_cap` for urllc (7->8) and
embb (7->10), plus `arrivals.ceiling_step_ratio: 0` so the ceiling is
structurally pinned regardless of what policy (if any) is pointed at
it -- not just empirically unused. mmtc's existing fixed point
(floor==nominal==cap==5) is unchanged. Validated: loads cleanly via
`load_saclb_config`, all three slices confirm `nominal_ratio ==
max_ratio_cap`, `ceiling_step_ratio == 0`.

## STOP

Estimate and verdict reported; config built and committed under
`experiments/configs/m47/`. Per this milestone's own gating, awaiting
go before M47-2 (offline training to extend the checkpoint pool).
