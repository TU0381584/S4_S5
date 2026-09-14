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

**The shed-classification split, at power, across 4 arms, on a FRESH
eval draw** (new `--seed` / admission-arrival realization, distinct
from every eval_seed already used in MR3/MR3c/PF2-1a, so the primary
powered campaign is not simply re-scoring already-seen draws).

**Discriminating prediction**: DQN-SLA classifies `correct_shed`
(urllc's per-window `C_urllc` compliance high, embb sacrificed) more
often than DQN-QoE, which classifies `indiscriminate_failure` (embb
sacrificed AND urllc still fails) more often than DQN-SLA, at the E4
co-located overload regime. This is the pattern already seen in 14/14
prior run-arm observations (MR3 + MR3c + PF2-1a combined) -- the
pre-registered claim is that it HOLDS UP on data none of those prior
observations touched, not that it will be discovered fresh.

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
static-at-cap arm (precedent: `saclb_campaign_static_at_cap_v2.yaml`
from Paper #4's own submitted campaign -- **NOTE, flagged not
resolved here**: that exact config predates the M41 ratio-floor fix
and the MR1 band-alignment rework, so PF2-1c needs a static-at-cap
variant built on `saclb_m46_train.yaml`'s own calibrated bands, not a
direct reuse of the old file; scoping that variant is PF2-1c's own
first step, not this document's).

**Paired test**: paired (by seed) two-sided t-test on PWC, matching
PF2-1a's own method exactly (same metric, same pairing logic, applied
fresh to the new draw) -- SLA vs QoE as the primary discriminating
pair; DQN arms vs static-at-cap and vs the non-ML baseline as the
secondary comparisons per GATE PF2-1c's own question (2).
Significance threshold alpha=0.05, two-sided, paired on seed.

**n**: the power fork below (not resolved in this document).

**Confirmation vs disconfirmation, fixed in advance**: the
pre-registered claim is CONFIRMED if DQN-SLA's PWC significantly
exceeds DQN-QoE's on the fresh draw (paired t-test, alpha=0.05) AND
the shed-classification pattern (SLA leaning `correct_shed`, QoE
leaning `indiscriminate_failure`) replicates directionally. It is
DISCONFIRMED if the difference is not significant at the pre-
registered n, or if the classification pattern reverses or becomes
inconsistent. A significant result at an UNDERPOWERED n (see the fork
below) is reported as suggestive, not confirmatory -- this project has
already seen a result of this exact shape (small-n significant,
p=0.0149) collapse entirely once properly powered (Stage 3->10,
Paper #4/CACS26 history, n=46, p=1.0) and treats that as binding
precedent for how any PF2-1c result at n=6 must be read.

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
