# M45-PF2-1 — pre-registration

Written and committed BEFORE any powered run, per this milestone's own
gating. States what is being tested, how, at what n, and what counts
as confirmation or disconfirmation -- fixed here, not adjusted after
seeing PF2-1c's results.

## What is NOT pre-registered, and why

MR4 predicted urllc's own commanded-ceiling-vs-backlog correlation
would be positive and embb's negative. PF2-1a (`docs/PAPER5_M45_PF21a_embb_confirmation.md`)
already measured both, live, before this document was written: embb
came out coherently negative (matching the prediction, 9/10 combined
observations); urllc came out coherently NEGATIVE too (8/10,
contradicting the original positive prediction). **Because this was
already observed, writing it down now as a "prediction" would be
postdiction, not prediction -- it is documented below as
characterization (what was found and the mechanism that explains it),
never as a pre-registered hypothesis this campaign tests.** Likewise
the reject-mechanism decomposition
(`docs/PAPER5_M45_PF21b_reject_decomposition.md`) is characterization
of already-collected data, not something PF2-1c is testing fresh.

## What IS pre-registered

**REVISED 2026 (M47-1)**: the primary claim below was updated after
M47-1's NO-RIG estimate (`docs/PAPER5_M47_1_static_at_cap_estimate.md`)
found DQN-SLA has converged, live, to a policy behaviorally
near-indistinguishable from static-at-cap for both controllable
slices (94.5-100.0% of urllc samples and 89.3-97.4% of embb samples
sit at the exact calibrated cap, in all 7 DQN-SLA runs collected to
date, zero exceptions) -- i.e., PF2-1b's own decomposition finding
("SLA protects urllc only by leaving ceilings wide open; the
scheduler does the work") is not just directionally true but
QUANTITATIVELY close to literal. This is still untested AT POWER (no
run has yet compared static-at-cap's actual live outcome against
DQN-SLA's side by side), so it is honestly pre-registrable as a fresh
claim -- unlike the per-slice sign, which PF2-1a already measured.

**The shed-classification split, at power, across 4 arms, on a FRESH
eval draw** (new `--seed` / admission-arrival realization, distinct
from every eval_seed already used in MR3/MR3c/PF2-1a, so the primary
powered campaign is not simply re-scoring already-seen draws).

**Primary discriminating prediction (three-way, per M47-1)**:
static-at-cap and DQN-SLA are statistically indistinguishable on PWC
and shed-classification (both lean `correct_shed`), while DQN-QoE is
significantly worse than BOTH (leans `indiscriminate_failure`) -- i.e.,
**learned admission control does not beat a trivial, non-adaptive
policy at this regime, and the QoE reward's learned behavior actively
makes outcomes worse, not better.** The original two-arm claim (DQN-SLA
`correct_shed` more often than DQN-QoE) is retained as a component of
this -- already seen in 14/14 prior run-arm observations (MR3 + MR3c +
PF2-1a combined), and the pre-registered claim is that it HOLDS UP on
data none of those prior observations touched, not that it will be
discovered fresh.

**Metrics, exactly as computed by the existing, unmodified
`m45_priority_weighted_correctness.py`** (reused across every prior
milestone in this family, not re-derived): PWC (priority-weighted,
`w_urllc=5.0`/`w_embb=3.5`, matching the submitted
`saclb_campaign_v2.yaml`), PWC_eq (equal-weight variant), and the
4-way shed classification (`correct_shed` / `indiscriminate_failure` /
`priority_inversion` / a 4th "no shed needed" case where neither slice
is under real stress). Computed from real radio-layer instruments
(RLC AM reject fraction, corrected `iperf3` throughput parsing, M41DBG
scheduler state) -- **never** `sla_compliance_all_slices` (P0's own
finding, `docs/PAPER5_M45_PF1_priority_weighted_correctness.md`:
structurally blind to exactly the starvation failure mode this
campaign is checking for).

**Arms**: DQN-QoE, DQN-SLA (MR2's existing checkpoints, MR1's config,
unedited), a non-ML baseline (`LbOnlyHeuristic`, `algorithm="lb_only"`
in `mc_runner.py` -- already-implemented, no new code), and a
static-at-cap arm -- config now built and committed
(`experiments/configs/m47/saclb_m47_static_at_cap.yaml`, M47-1),
a variant of `saclb_m46_train.yaml` with `nominal_ratio` raised to
equal `max_ratio_cap` and `ceiling_step_ratio: 0`, NOT a reuse of the
pre-M41-fix `saclb_campaign_static_at_cap_v2.yaml`.

**Paired test**: paired (by seed) two-sided t-test on PWC, matching
PF2-1a's own method exactly (same metric, same pairing logic, applied
fresh to the new draw). Primary pair: DQN-SLA vs static-at-cap (tests
the three-way claim's "≈" -- expects NO significant difference) and
DQN-QoE vs the better of {DQN-SLA, static-at-cap} (expects a
significant deficit for QoE). DQN-SLA vs DQN-QoE (the original two-arm
claim) and both DQN arms vs the non-ML baseline are secondary
comparisons per GATE PF2-1c's own question (2). Significance threshold
alpha=0.05, two-sided, paired on seed throughout.

**n**: the power fork below (not resolved in this document).

**Confirmation vs disconfirmation, fixed in advance**: the
pre-registered THREE-WAY claim is CONFIRMED if (a) DQN-SLA vs
static-at-cap shows NO significant PWC difference (paired t-test,
alpha=0.05) AND their shed-classifications agree (both lean
`correct_shed`), AND (b) DQN-QoE's PWC is significantly lower than
BOTH on the fresh draw AND its shed-classification leans
`indiscriminate_failure`. It is DISCONFIRMED if static-at-cap
significantly UNDERperforms DQN-SLA (a genuine learned-SLA component
would exist beyond staying wide open) or if DQN-QoE is not
significantly worse than the other two. The original two-arm claim
(DQN-SLA `correct_shed` more than DQN-QoE) is confirmed/disconfirmed
by the same criteria as before, independently of the three-way result.
A significant result at an UNDERPOWERED n (see the fork below) is
reported as suggestive, not confirmatory -- this project has already
seen a result of this exact shape (small-n significant, p=0.0149)
collapse entirely once properly powered (Stage 3->10, Paper #4/CACS26
history, n=46, p=1.0) and treats that as binding precedent for how any
PF2-1c result at n=6 must be read.

## Power fork -- for supervisor decision (Pang/Phang), not resolved here

From PF2-1a's paired-PWC effect size (n=5, d=3.52 observed): required
n for 80% power at alpha=0.05 is 1 (raw, untrusted), 3 (conservative,
effect halved), or 11 (very conservative, effect quartered -- still a
conventionally "large" effect size, and the bar this pre-registration
treats as the real target). **11 exceeds MR2's entire 6-seed
checkpoint pool (256-261).**

- **(a) n=6** (every existing seed, one -- 261 -- not yet run live):
  clears the conservative bar, falls short of the very-conservative
  one by design. If chosen, PF2-1c's own report must state this
  plainly rather than let a small-n significant result read as
  confirmatory on its own (see precedent above).
- **(b) train more seeds first**: reaches the very-conservative bar,
  at a real offline-training time cost, before any further live rig
  time is spent.

## Replication batch

Independent of which fork is chosen: re-run the SAME checkpoint set
(whichever seeds the primary sample used) under a SECOND fresh
eval_seed, distinct from both the primary sample's eval_seed and every
eval_seed already used in MR3/MR3c/PF2-1a. This is the maximum
independence available without new training (the checkpoint-seed pool
is capped at 6 -- see the fork above) -- it tests robustness to a
different admission-arrival realization, not a different trained
policy.

## STOP

Pre-registration committed. Per M45-PF2-1's own gating, PF2-1c does
not launch until the power fork above is decided.
