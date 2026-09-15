# GATE PF2-1c — 5-arm powered campaign, PRIMARY DRAW ONLY (preliminary / unreplicated)

**Status: preliminary.** The pre-registered independent replication
draw was stopped at 5/30 runs by explicit user decision mid-campaign
(see the ADDENDUM in `docs/PAPER5_M47_PF21c_plan_and_deviation.md`).
Reporting criterion #2 below ("does the ranking hold on an
independent draw") is therefore **not answered** by this report —
only the primary draw (n=6/arm, 30 live runs, all completed cleanly,
100% coupling/in-band pass) is analyzed here. Read this document as
a single powered-ish draw, not as a replicated finding, per this
project's own repeated precedent (Stage 3→10: an n-small significant
result at p=0.0149 collapsed to p=1.0 once properly powered).

Data: `experiments/results/m47_pf21c/manifest.csv` (primary rows
only). Analysis: `experiments/scripts/m47_pf21c_analysis.py`. Metrics:
PWC / PWC_eq / 4-way shed-classification from
`m45_priority_weighted_correctness.py` (unmodified), never
`sla_compliance_all_slices`. All 30 primary runs: `coupling_pass=True`,
`in_band_pass=True` (zero uncapped samples in the clean window for
every run). `responsiveness_pass` was `True` for 29/30 runs; the one
`False` (run 16, static_cap/264) is the expected, previously-noted
zero-ceiling-variance case for a frozen arm, not a defect.

## 1. Per-arm summary (primary draw, n=6/arm)

| arm | PWC mean [95% CI] | PWC_eq mean [95% CI] | shed classes (n=6) |
|---|---|---|---|
| dqn_qoe | 0.5275 [0.4361, 0.6196] | 0.4755 [0.3885, 0.5634] | 4 indiscriminate_failure, 2 correct_shed |
| dqn_sla | 0.7025 [0.6988, 0.7060] | 0.6388 [0.6343, 0.6430] | 6 correct_shed |
| static_cap | 0.7036 [0.7026, 0.7046] | 0.6401 [0.6390, 0.6413] | 6 correct_shed |
| static_floor | 0.4362 [0.4272, 0.4426] | 0.3834 [0.3758, 0.3889] | 6 indiscriminate_failure |
| lb_only | 0.5689 [0.5504, 0.5877] | 0.5042 [0.4882, 0.5202] | 6 correct_shed |

## 2. Paired comparisons (slot-paired, n=6; bootstrap 95% CI on mean
difference, paired t-test, Wilcoxon signed-rank)

PWC (priority-weighted, w_urllc=5.0):

| comparison | mean diff | 95% CI | paired-t p | Wilcoxon p |
|---|---|---|---|---|
| static_cap − dqn_sla | +0.0011 | [−0.0026, +0.0054] | 0.650 | 0.844 |
| dqn_sla − dqn_qoe | +0.1751 | [+0.0826, +0.2652] | 0.022 | 0.0625 |
| static_cap − dqn_qoe | +0.1761 | [+0.0830, +0.2677] | 0.022 | **0.0312** |
| static_cap − static_floor | +0.2674 | [+0.2610, +0.2770] | <0.0001 | **0.0312** |
| static_cap − lb_only | +0.1347 | [+0.1154, +0.1540] | 0.0001 | **0.0312** |
| dqn_sla − lb_only | +0.1336 | [+0.1141, +0.1528] | 0.0001 | **0.0312** |

PWC_eq (equal weight) — same sign, same significance pattern
throughout, no ranking flip: static_cap−dqn_sla n.s. (p=0.651/0.844);
all other five pairs significant at essentially the same magnitude
(0.0000–0.0236 t-test, 0.0312–0.0625 Wilcoxon). **The priority
weighting does not drive any qualitative conclusion in this
campaign** — every finding below holds under equal weighting too.

(0.0312 is the minimum achievable two-sided Wilcoxon p at n=6 with
fully sign-consistent differences — five of six comparisons hit that
floor, i.e. every one of the 6 paired slots agreed on the direction
of the effect.)

## 3. Findings against the pre-committed questions

**Does static-at-cap ≈ DQN-SLA?** Yes — mean difference +0.0011 PWC,
not significant (p=0.65/0.84), tightly overlapping CIs. Confirms
M47-1's earlier distributional finding now as a formal paired test:
DQN-SLA's live behavior is statistically indistinguishable from a
policy that simply freezes the ceiling at cap and lets the scheduler
do the work.

**Do both static-at-cap and DQN-SLA outperform DQN-QoE?**
static_cap−dqn_qoe reaches full significance (p=0.022 t, p=0.0312
Wilcoxon — every slot sign-consistent). dqn_sla−dqn_qoe is
significant on the paired t-test (p=0.022) but not on Wilcoxon
(p=0.0625): one of six slots broke sign-consistency. That slot is
**263**, where dqn_qoe scored 0.7017 vs dqn_sla's 0.7016 — a
near-exact tie, not a real reversal — and **261** also shows a much
smaller-than-typical gap (dqn_qoe 0.6879 vs dqn_sla 0.7076). These
are precisely the two seeds M47-2-2/M47-3-0 flagged as the qoe pool's
divergent/variance-prone checkpoints (261's `correct_shed` divergence
reproduced again in this campaign at run 21; 263 showed
eval_seed-sensitivity across M47-2-2 vs run 19 here). **This is the
mechanism, visible directly in the paired data**: DQN-QoE's average
deficit is real and large in 4 of 6 seeds, but the two seed-lottery
checkpoints pull the nonparametric test just under the conventional
significance line. Per M47-3-0's own framing, this is a probabilistic
effect, not a deterministic one, and 261/263 are not excluded — they
are exactly what is producing the borderline result, reported as
such rather than resolved either way.

**Does static-at-floor discriminate from static-at-cap?** Yes,
strongly — mean difference +0.267 PWC, p<0.0001 (t), p=0.0312
(Wilcoxon, floor-of-n=6), 6/6 slots `indiscriminate_failure` vs 6/6
`correct_shed`. This directly confirms M47-2-0's design rationale for
adding static-at-floor as a second reference: a frozen, non-adaptive
ceiling is not by itself sufficient for urllc protection — its
**value** matters. The scheduler alone does not rescue urllc when the
ceiling is pinned at the floor.

**Does lb_only differ from the frozen statics?** Yes, in a genuinely
new way. lb_only classifies `correct_shed` in all 6 slots — matching
static_cap and dqn_sla qualitatively — but scores significantly
*lower* in PWC than either (static_cap−lb_only p=0.0001/0.0312,
dqn_sla−lb_only p=0.0001/0.0312, both fully sign-consistent). The
reactive quota-threshold heuristic protects urllc *in kind* but not
*to the same degree* as either the DQN-SLA policy or a ceiling simply
frozen at cap — a real, mechanistically-distinct middle position
between the two static extremes, not a redundant third arm.

## 4. What is NOT established by this report

- **Independent-draw replication** (criterion #2 of the original
  GATE spec) — not completed. The 5 replication rows collected before
  the stop (slots 258/260/264, arms dqn_sla/lb_only/static_floor)
  all matched their primary-draw `shed_classification` exactly (5/5),
  which is a reassuring but explicitly informal spot-check, not a
  powered test — it covers 3 of 5 arms and 3 of 6 slots, and was
  never intended as a designed sub-sample.
- The dqn_sla > dqn_qoe gap's Wilcoxon significance specifically
  (p=0.0625, just above 0.05) — flagged above as seed-lottery-driven,
  not resolved.
- Any claim beyond this specific live-rig configuration (E4
  co-located regime, cold-start, this checkpoint pool) — no
  generalization tested.

## 5. Recommendation

Given (1) above are established with full slot-level sign-consistency
for 4 of 6 comparisons and (2) the qualitative pattern is exactly what
every prior milestone in this line (M45 PF2-1a/b, M47-1, M47-2-0)
already predicted, this is a coherent and internally consistent
primary-draw result — but it is reported here as **preliminary**, and
should not be cited in the manuscript as a replicated finding. If the
paper needs the replicated version of this claim, the remaining 25
replication runs (~6.25 hours at the observed ~15min/run pace) are
the direct path to it; the run order and eval-seed mapping are already
fixed in `docs/PAPER5_M47_PF21c_plan_and_deviation.md` and require no
new design work to resume.

## STOP

Per the original PF2-1c task specification: reporting stops here.
Awaiting go before any M39 manuscript restructure.
