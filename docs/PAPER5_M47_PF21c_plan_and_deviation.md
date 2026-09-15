# M47-PF2-1c — execution plan and pre-registration deviation (fixed BEFORE any run)

## Deviation from the original pre-registration, explicit and logged

`docs/PAPER5_M45_PF21_preregistration.md` specified the DQN arms at
their full 12/12 pooled trustworthy checkpoints. Given the true scale
of a fully-crossed 5-arm design at n=12/arm (12 slots x 5 arms x 2
draws = 120 live runs, ~32 hours at this project's own observed
~16min/run pace -- an order of magnitude beyond any prior single
campaign, with real cumulative-session risk per Stage 15/M38
precedent), the user was asked directly (not decided unilaterally)
and chose: **n=6/arm for ALL 5 arms, both draws** (30 primary + 30
replication = 60 runs total, ~16 hours), executed as continuous
batches across as many sessions as needed, same discipline as
M47-2-2. This is a real, logged deviation from the pre-registration's
stated n, not a silent substitution -- reported here and in the
eventual GATE PF2-1c report exactly as such.

## Checkpoint-seed selection -- random, fixed before any result, 261 included by chance not choice

`random.seed(4721); random.sample(seeds_12, 6)` over MR2's full
12-seed pool -- chosen: **258, 260, 261, 263, 264, 267**. Same 6
seed-numbers used for BOTH DQN-QoE and DQN-SLA (preserves the
pre-registration's paired-by-seed-number design). **Seed 261 (M47-3's
seed-lottery outlier) landed in the draw by chance, not by
inclusion-forcing or exclusion** -- per M47-3-0's own instruction that
it stays in the pool as data, this is the fair, unbiased way to honor
that: a genuinely random draw that happened to include it, not a
deliberate choice either way.

## Eval-seed assignment -- one per slot, shared across all 5 arms in that slot

New range, clearly separated from every eval_seed used in any prior
milestone (MR3: 950-953; PF2-1a: 954-959; M47-2-2/3: 969-975,
1069-1075): **primary draw 2001-2006, replication draw 2101-2106**,
one eval_seed per slot, the SAME eval_seed used across all 5 arms
within that slot (the natural pairing unit for arms with no training-
seed identity of their own -- static-at-cap/floor/lb_only are matched
to a slot's environmental arrival-process draw, not a checkpoint).
Verified independent (not assumed): `np.random.RandomState(seed)` for
all 12 new eval_seeds produces 12 distinct draws, confirmed directly.

| slot | DQN checkpoint seed | primary eval_seed | replication eval_seed |
|---|---|---|---|
| 1 | 258 | 2001 | 2101 |
| 2 | 260 | 2002 | 2102 |
| 3 | 261 | 2003 | 2103 |
| 4 | 263 | 2004 | 2104 |
| 5 | 264 | 2005 | 2105 |
| 6 | 267 | 2006 | 2106 |

## Arm/config/algorithm mapping

Extended `m46_mr3_live_revalidate.run_one()` with optional
`algorithm`/`config_override`/`checkpoint_override`/`reward_mode_override`
parameters (backward compatible -- every prior caller's positional-
only invocation is byte-identical in behavior; verified via
`py_compile` and by tracing the exact xapp_cmd construction against
the pre-change version). No frozen source touched -- this is this
project's own live-orchestration script, already extended in every
prior M4x/PF2-1x milestone.

| arm | config | algorithm | checkpoint | reward-mode |
|---|---|---|---|---|
| DQN-QoE | `saclb_m46_train.yaml` | dqn | per-slot qoe checkpoint | qoe |
| DQN-SLA | `saclb_m46_train.yaml` | dqn | per-slot sla checkpoint | sla |
| static-at-cap | `experiments/configs/m47/saclb_m47_static_at_cap.yaml` | lb_only | none | sla |
| static-at-floor | `experiments/configs/m47/saclb_m47_static_at_floor.yaml` | lb_only | none | sla |
| lb_only (non-ML baseline) | `saclb_m46_train.yaml` | lb_only | none | sla |

`lb_only` used for the two static arms specifically because
`saclb_xapp.py` requires no `--checkpoint` only for that algorithm
(`argparse`'s own check) -- under `ceiling_step_ratio=0`,
`LbOnlyHeuristic`'s own accept/reject decisions are structurally
inert (the ceiling cannot move regardless of what it decides), so the
REALIZED ceiling trajectory is exactly "frozen at cap/floor" as
intended, without needing to arbitrarily borrow a DQN checkpoint whose
actions would be equally inert under the same config. `reward-mode
sla` chosen for all 3 non-learning arms as a neutral default (no
learning signal is being driven by it; matches this project's own
established eq.2 baseline convention for non-QoE-specific comparator
arms).

## Metrics (unchanged from pre-registration)

PWC, PWC_eq, 4-way shed-classification from real radio-layer instruments
(`m45_priority_weighted_correctness.py`, unmodified) -- never
`sla_compliance_all_slices`. In-band/coupling checks logged as
characterization (same method as M47-2-2) but do NOT gate a run's
inclusion in PF2-1c's matrix -- unlike the trust-gate milestones, a
non-learning arm reading out-of-band or a DQN arm's live behavior
diverging is itself part of what this campaign measures, not a
reason to exclude a result.

## Run order -- randomized, fixed in advance

30 primary-draw (slot, arm) pairs, `random.seed(47213)`, shuffled
once, not re-rolled. Batched 4 per session (matching M47-2-2's own
successful batch size), manifest committed after EVERY run.

```
1  (260,dqn_sla)      9  (267,lb_only)      17 (264,lb_only)      25 (264,dqn_qoe)
2  (260,lb_only)      10 (258,dqn_qoe)      18 (258,static_cap)   26 (267,dqn_sla)
3  (258,static_floor) 11 (263,static_floor) 19 (263,dqn_qoe)      27 (260,static_floor)
4  (258,dqn_sla)      12 (261,dqn_sla)      20 (267,dqn_qoe)      28 (264,dqn_sla)
5  (264,static_floor) 13 (263,lb_only)      21 (261,dqn_qoe)      29 (263,static_cap)
6  (267,static_cap)   14 (261,lb_only)      22 (260,dqn_qoe)      30 (267,static_floor)
7  (261,static_cap)   15 (260,static_cap)   23 (263,dqn_sla)
8  (258,lb_only)      16 (264,static_cap)   24 (261,static_floor)
```

The replication draw (eval_seeds 2101-2106) reuses this exact order
with the eval_seed swapped -- not re-randomized, so any ordering
effect is identical across both draws.

## STOP-equivalent: plan committed before any run

Per this milestone's own "pre-commit metrics, no relaxation" standing
constraint. Execution begins after this commit.

## ADDENDUM (post-execution): replication draw stopped early, by explicit user decision

The primary draw ran to completion (30/30 runs). The replication draw
was **not completed** -- it was stopped at run 5/30 by an explicit,
direct user instruction given mid-campaign ("option 2": stop now,
report primary-only, explicitly labeled preliminary/unreplicated),
after I raised the time-cost-vs-value tradeoff and the user chose to
accept the weaker evidentiary position rather than spend the
remaining ~6.5 hours. This is a second, real, logged deviation from
the pre-registration -- reported here exactly as such, same as the
n=6/arm deviation above.

**Consequence for GATE PF2-1c's own pre-committed reporting
criterion #2** ("does the three-way ranking + the DQN split hold on
the independent draw, or move -- cf. Stage 3->10 precedent"): this
question is **UNANSWERED**, not answered favorably. Only 5 of the 30
replication (slot, arm) pairs were ever run, and those 5 were not
selected as a designed sub-sample -- they are simply the first 5 in
the pre-committed random run order. They are reported in
`docs/PAPER5_M47_PF21c_gate_report.md` as an informal spot-check
(all 5 matched their primary-draw shed_classification), but this is
explicitly NOT a substitute for a powered independent replication,
and must not be read as one. The GATE report's findings are
preliminary on the primary draw alone.

Also noting, for the record, two premature/incorrect arm-completion
claims made in commit messages during execution (verified now against
the final manifest, not against the commit messages themselves):
run 23's commit claimed "dqn_sla arm complete for primary draw, 6/6"
-- this was wrong, dqn_sla was actually 4/6 at that point and reached
6/6 only at run 28. Run 24's equivalent claim about static_floor
(also wrong at the time, "4/4" when the arm has 6 total slots) was
caught and corrected in-conversation at the time; the run-23 error
was not caught until this addendum. Neither affected the manifest
data itself (only prose in commit messages), and the true per-arm
completion is what `experiments/results/m47_pf21c/manifest.csv`
shows directly, not any interim commit-message claim.
