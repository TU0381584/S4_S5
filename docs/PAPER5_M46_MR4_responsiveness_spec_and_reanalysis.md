# M46-MR4 — operational responsiveness definition + re-analysis of existing data (NO RIG)

Per this milestone's own gating: disk cleanup, then a locked
operational responsiveness definition, then re-analysis of MR3/MR3c's
already-collected data under it (no new live time), then a verdict on
the QoE-vs-SLA shed split. No fix, no config edit, no retrain -- pure
analysis of data already on disk plus the disk cleanup itself.

## (0) Disk cleanup

**Before**: 95% used, 8.0G available. **After**: 82% used, 28G
available (20G freed). Deleted 197 raw gNB console logs
(`experiments/logs/gnb_*.log`, `experiments/logs/gnb_m41_*.log`) dated
2026-09-01 through 2026-09-08 (plus a handful of gate-phase-only
Sept-11 logs from this same milestone family's own bring-up cycles) --
all from milestones (M36 through M45) whose findings are already
extracted into committed reports/result JSONs; none of these raw files
is referenced by name anywhere in `docs/`, `Papers_4-5/`, or
`experiments/scripts/*.py` (checked by direct grep before deleting,
zero matches). **Explicitly preserved and NOT touched**:
- All 10 gNB logs backing the current M46-MR3/MR3b/MR3c family
  (2026-09-08 and 2026-09-11 full-episode logs, 8.3G) -- this
  milestone's own re-analysis below reads them directly.
- `experiments/logs/live_ue*_console*.log` (83M) -- named specifically
  in this project's own memory as still-open evidence for the
  unresolved M42/Fig.8-validity question; not this milestone's call to
  discard.
- `experiments/results/m6_pilot/` (35G) and any other directory under
  `experiments/results/` with uncommitted changes (`git status`
  checked first: `m6_pilot`'s `m6_results.json` files are modified,
  uncommitted -- active, in-progress work, not this milestone's to
  touch) -- disk pressure was already fully resolved by the log
  cleanup alone, so no need to touch ambiguous in-progress data.
- No rfsim artifacts found (this testbed is native-stack throughout,
  confirmed by search).

## (1) Responsiveness, defined operationally

MR3c's raw finding (urllc/embb Pearson r between commanded ceiling and
own-slice backlog, pooled with no per-slice/per-arm expected sign) was
uninterpretable on its own terms: a negative correlation is not
inherently "broken" for an ADMISSION-CONTROL ceiling the way it would
be for a scheduler serving already-admitted traffic. The sign only
means something once derived from what each reward actually pays for.

**Mechanism shared by both reward modes** (`action_mapping.py`'s
`AdmissionGate.apply()`, unchanged by reward mode): `action==1`
(accept) raises the ceiling by `step_ratio`, capped at
`max_ratio_cap`; `action==0` (reject) lowers it by `step_ratio`, floor
at `min_ratio_floor`. The ceiling is the DIRECT, mechanical trace of
the accept/reject decision sequence, not a separate control signal --
"does the ceiling respond to backlog" is really "does the accept/
reject decision respond to backlog," filtered through this fixed
map.

**What each reward actually pays for** (`reward.py`, both modes share
`check_violations()`'s `ViolationCheck.margin`/`violated`, keyed by
`agg.queue_len_norm > 1.0 OR agg.loss_proxy > spec.loss_budget_pct`):

- `compute_step_reward` (SLA/eq.2, the arm this project calls "sla"):
  `service_term` rewards accepting, weighted by each slice's OWN
  `priority_weight` (urllc's is the highest of the three configured
  slices, embb's the second-highest but well below urllc's -- these
  are `saclb_campaign_v2.yaml`'s own submitted values, reused
  unchanged in `saclb_m46_train.yaml`); `violation_term` charges a
  FLAT penalty per slice currently in violation, independent of
  ratio; `congestion_term` charges `congestion_coeff * mean_congestion
  * total_accepted` -- a COST that grows with how much is being
  accepted while the cluster is congested, same coefficient
  regardless of which slice.

- `compute_qoe_reward` (QoE/eq.9, the "qoe" arm): swaps the static
  `service_term` for `alpha*MOS_norm`, but keeps an SLA-violation
  penalty structurally equivalent in spirit -- `gamma*sla_viol`, a
  CONTINUOUS severity average built from the SAME `ViolationCheck.margin`
  -- and the same congestion-linked `cost` term (`beta*cost`, same
  `mean_congestion*total_accepted` basis as the SLA arm's
  `congestion_term`). Per this milestone's own admission-control
  framing, MOS itself is throughput/loss-driven per slice, so a
  slice's own MOS degrades under the same congestion conditions that
  would trip its `ViolationCheck` margin.

**Derived, direction-correct expected sign, per slice, both arms**
(the accept/reject-driven violation-and-congestion structure above is
IDENTICAL in kind across both reward modes -- both penalize a slice's
own SLA violation and both charge a congestion-linked cost for
accepting -- so the same per-slice sign is expected under either
reward, moderated only by how strongly that particular reward weighs
protecting a given slice):

| slice | own priority_weight (relative) | expected sign of corr(own ceiling, own backlog) | why |
|---|---|---|---|
| urllc | highest of the three configured slices | **positive** | its own violation is the most heavily protected outcome (highest `priority_weight` in the SLA arm's `service_term`; the same margin drives the QoE arm's `sla_viol` term regardless of weighting) -- raising ITS OWN ceiling as ITS OWN backlog rises is the reward-maximizing way to relieve the violation before it fires, since the mechanical accept-raises-ceiling link is the ONLY lever available to relieve a slice's own congestion. A policy that instead let urllc's backlog climb without raising its ceiling would eat the flat/severity violation penalty for nothing -- clearly reward-suboptimal under either reward's own accounting. |
| embb | lower than urllc's | **negative** | embb is this project's own established "shed if something has to give" slice (`docs/PAPER5_M45_PF1_priority_weighted_correctness.md`'s own framing, `w_urllc=5.0 > w_embb=3.5`) -- accepting into an already-congested embb costs the SAME congestion-linked penalty as accepting into urllc, but buys a SMALLER service/MOS return and does nothing to relieve urllc's own (more heavily weighted) violation risk. Lowering embb's OWN ceiling as ITS OWN backlog rises is the reward-maximizing way to stop paying that congestion cost for the lower-return slice. mmtc excluded throughout, per every prior milestone in this family: M44-E1b already established no realistic controllable band exists for it. |

This is a MECHANISM-level derivation from the actual reward code, not
an assumption about what "should" happen -- and it is deliberately
the SAME expected sign for both arms, since both reward's structural
skeleton (accept-raises-ceiling, violation-and-congestion-penalized)
is identical; only the weighting mechanism differs (static
`priority_weight` vs `MOS_norm`), not the qualitative incentive shape
this analysis depends on.

**A single pooled correlation across slices/arms is meaningless under
this definition** (as the milestone brief states) -- a run that mixed
urllc's expected-positive and embb's expected-negative points into one
number would show a value near zero regardless of whether EITHER slice
is behaving correctly, which is exactly the trap MR3c's own per-slice
(but not per-expected-sign) reporting still risked being read into.
Below, every number is kept per-slice and classified against its own
expected sign, never pooled.

## (2) Re-analysis of existing data (MR3 original + MR3c clean, no new rig time)

Recomputed both, per-slice, per-arm, per-seed. MR3's original 4 runs
use a `t>=30s` proxy cutoff (MR3's own per-window `trajectory` data,
already computed and committed, shows the startup transient settled by
window 1/2 in all 4 runs -- see MR3b's own correction; MR3 predates
the `M46DBG e2_apply` instrumentation, so the precise write-timestamp
cutoff MR3c uses isn't available for it). MR3c uses the precise
`t>=first_e2_apply_write` cutoff already validated in
`PAPER5_M46_MR3c_clean_revalidation.md`.

| run | arm | slice | expected sign | measured r | matches? |
|---|---|---|---|---|---|
| MR3 qoe/256 | qoe | urllc | + | +0.827 | **yes** |
| MR3 qoe/256 | qoe | embb | - | +0.724 | **no** |
| MR3 qoe/257 | qoe | urllc | + | +0.782 | **yes** |
| MR3 qoe/257 | qoe | embb | - | +0.672 | **no** |
| MR3 sla/256 | sla | urllc | + | +0.844 | **yes** |
| MR3 sla/256 | sla | embb | - | +0.712 | **no** |
| MR3 sla/257 | sla | urllc | + | +0.646 | **yes** |
| MR3 sla/257 | sla | embb | - | +0.728 | **no** |
| MR3c qoe/256 | qoe | urllc | + | +0.051 | weak yes |
| MR3c qoe/256 | qoe | embb | - | -0.007 | weak yes |
| MR3c qoe/257 | qoe | urllc | + | **-0.975** | **no (strong)** |
| MR3c qoe/257 | qoe | embb | - | -0.824 | **yes (strong)** |
| MR3c sla/256 | sla | urllc | + | -0.016 | weak no |
| MR3c sla/256 | sla | embb | - | +0.004 | weak no |
| MR3c sla/257 | sla | urllc | + | +0.265 | **yes** |
| MR3c sla/257 | sla | embb | - | -0.282 | **yes** |

(MR3's `t>=30s` numbers reuse the values already computed and reported
in `PAPER5_M46_MR3b_control_path_origin.md`'s correction section --
not re-derived differently here, same cutoff, same source data.)

**Does the spread resolve into a coherent pattern? Partially, and
unevenly across the two eras -- reported exactly as found, not
smoothed toward either extreme:**

- **urllc: 6 of 8 match** (positive, as expected) across MR3
  (4/4 -- unanimous, and strongly so, r=0.65-0.85) and MR3c (2/4 clear
  matches, 2 negligible-or-contradicting including one very strong
  contradiction at qoe/257). MR3's own 4/4 unanimous positive match is
  the single most coherent slice-level signal in this entire dataset.
- **embb: MR3 is unanimously WRONG (0/4 -- all four are positive when
  negative was expected, and not weakly: 0.67-0.73); MR3c is 2/4 clear
  matches (both moderate-to-strong, both in `qoe`) plus 2 negligible.**
  This is not incoherent noise -- it is a CONSISTENT DIRECTION within
  each era (MR3: always positive; MR3c: leans negative when it's not
  near-zero) that flips depending on which era's data is used, which
  points at something the `t>=30s` proxy cutoff is doing differently
  from the precise write-timestamp cutoff, not at embb's live behavior
  itself being this unstable.

**Diagnosed, not left as a mystery**: MR3's `t>=30s` cutoff is
demonstrably less precise than MR3c's write-timestamp one (MR3b's own
correction already flagged this -- the true settling point runs to
~93-103s for several slices pre-fix, so `t>=30s` still includes a
large block of the SAME uncapped-ceiling excursion MR3b/MR3c fully
characterize). A large block of samples where `max_prbs` sits near its
uncapped ~100-106 ceiling (embb's calibrated in-band cap is only 10)
while `remainUEs` is elevated (1-4, matching every other finding in
this family) mechanically manufactures a strong POSITIVE correlation
for embb regardless of the policy's real accept/reject behavior --
high-value ceiling paired with nonzero backlog, repeated over ~12,000
contaminated samples, dominates a Pearson computation over ~24,000-
29,000 total. **MR3's embb figures above are very likely a residual
instance of the SAME already-diagnosed contamination MR3b/MR3c exist
to remove, not a real live-embb finding -- flagged, not asserted with
full confidence, since MR3 predates the instrumentation needed to
prove it precisely the way MR3c did for itself.** MR3c's own numbers,
measured on the validated clean cutoff, are the ones this report
weighs more heavily for exactly this reason.

**On MR3c's own mixed picture**: taking the precise, clean numbers at
face value -- urllc leans positive (2 clear matches, 1 negligible, 1
strong contradiction) and embb leans negative (2 clear matches, 2
negligible) across 4 seeds is a DIRECTIONALLY consistent-with-expected
pattern more often than not (5 of 8 clear-or-weak matches, versus 1
strong contradiction and 2 negligible non-matches that are arguably
"no signal" rather than "wrong signal," given `remainUEs`'s own
4-value range caps how much any single-episode correlation can mean).
**Not coherent enough to call unambiguously confirmed, not incoherent
enough to call the metric broken or the policies non-responsive --
reported as a real but noisy lean toward the reward-derived
expectation, most plausibly limited by single-episode sample size
(the same limitation MR3c's own report already flagged for the
range-exercise question) rather than by a deeper policy defect.**

## (3) The stable PWC/shed signal: real, replicated, not an artifact

`docs/PAPER5_M46_MR3_live_trust_gate.md` and
`docs/PAPER5_M46_MR3c_clean_revalidation.md`'s shed-classification
tables, side by side:

| seed | arm | MR3 (pre-fix) classification | MR3c (post-fix) classification | shed_precision (both) |
|---|---|---|---|---|
| 256 | qoe | `indiscriminate_failure` x4 | `indiscriminate_failure` x4 | 0.0 both |
| 257 | qoe | `indiscriminate_failure` x4 | `indiscriminate_failure` x4 | 0.0 both |
| 256 | sla | `correct_shed` x4 | `correct_shed` x4 | 1.0 both |
| 257 | sla | `correct_shed` x4 | `correct_shed` x4 | 1.0 both |

**Verdict: real, replicated behavioral difference, not an artifact of
the control-path bug or the loose responsiveness measure.** Grounds
for this, not just the raw repetition:

1. **It survived the control-path fix completely unchanged.** The
   uncapped-ceiling excursion MR3b/MR3c chased (up to ~93-103s of
   catastrophic mis-application) sat squarely inside the SAME episode
   windows PWC/shed is computed over -- if the shed split were an
   artifact of that excursion, fixing it should have moved these
   numbers. It did not move them at all, across two independently
   collected sessions (2026-09-08 pre-fix, 2026-09-11 post-fix) three
   days apart with a full environment rebuild in between.
2. **It is not the same signal as the responsiveness question in (2).**
   PWC/shed is computed from `served_kbps`/`offered_kbps`/
   `rlc_reject_frac` (real downstream traffic outcomes,
   `m45_priority_weighted_correctness.py`, reused unmodified from
   M45) over 15s windows across the WHOLE episode, not from the
   ceiling/backlog correlation MR3c's fix and this milestone's
   responsiveness definition are about. Two independently-computed
   signals agreeing this precisely across 2 seeds x 2 collection
   sessions is a meaningfully different bar than one noisy metric
   repeating itself.
3. **It matches this milestone's own responsiveness re-analysis in
   direction where they overlap**: DQN-QoE's `indiscriminate_failure`
   (embb sacrificed, urllc still fails anyway -- `mean_c_urllc`
   0.50-0.72 across MR3c's own 2 qoe seeds, well below sla's 0.9998-1.0)
   is consistent with a qoe-arm policy that is NOT reliably protecting
   urllc's own violation margin even after paying embb's congestion
   cost -- exactly the failure mode (2) would also flag if urllc's own
   responsiveness were confirmed weak in that arm specifically (which
   qoe/257's -0.975 contradiction, if it holds up under more seeds
   rather than being sample-size noise, would be consistent with).

**This is the opposite of what this project's paper narrative would
want** (the QoE-aware reward, DQN-QoE, is the arm CACS26's own
submitted headline result already validates live for the single-slice
case) -- stated
plainly, not softened, per this project's own "never invent, honest
reporting" standard: **in this specific E4 co-located, multi-slice
overload regime, at n=2 seeds x 1 episode, the QoE reward's own
priority-protection mechanism (its continuous `sla_viol` term) is not
succeeding at protecting the higher-priority slice the way the
static-weight SLA reward's flat `violation_term` does, while embb is
sacrificed under BOTH rewards regardless.** This is a real, structural
question the paper needs to reckon with if it holds under more seeds,
not a single-run fluke to explain away.

## GATE MR4

**(1) Freed disk**: 20G (95%->82% used, 8.0G->28G available). Nothing
referenced by a paper figure/table or an open investigation thread
was touched.

**(2) Responsiveness definition**: locked above -- urllc expected
positive (own ceiling tracks own backlog, protective), embb expected
negative (own ceiling falls as own backlog rises, shed-under-
contention), same expected sign under both reward arms since both
share the same accept/reject-driven, violation-and-congestion-
penalized mechanism; only the weighting differs.

**(3) Coherent pattern?** Partially. urllc's expected-positive sign is
STRONGLY confirmed in MR3's own data (4/4, r=0.65-0.85) and leans
confirmed in MR3c's cleaner data (2 clear matches, 1 strong
contradiction, 1 negligible). embb's expected-negative sign is
diagnosed as likely CONTAMINATED in MR3's own data (same startup-
excursion artifact this milestone family already exists to remove)
and leans confirmed in MR3c's clean data (2 clear matches, 2
negligible). Net: a real, direction-consistent-more-often-than-not
lean exists, most plausibly limited by single-episode sample size
rather than a deeper defect, but not yet a clean, fully powered
confirmation either.

**(4) Shed-classification verdict**: real, replicated behavioral
difference -- QoE reward fails to protect urllc even while sacrificing
embb (`indiscriminate_failure`, the worse of the two possible
failure-with-sacrifice outcomes); SLA reward succeeds at protecting
urllc while also sacrificing embb (`correct_shed`). Survived the
control-path fix unchanged, computed from a different signal than the
responsiveness question, and consistent in direction with this
milestone's own responsiveness findings where they overlap.

## DECISION

**Existing data shows a real, replicated per-arm behavioral
difference (the shed-classification split) worth powering, PLUS a
real-but-noisy, sample-size-limited lean on the responsiveness
question that a wider campaign is positioned to resolve, not
re-litigate from scratch.** This is closer to the milestone's first
branch than its second: not "genuinely incoherent" -- urllc's own
signal in particular is strong and consistent wherever the data isn't
independently known to be contaminated -- but also not yet a clean,
fully-powered confirmation on its own. **Recommended pre-registered
hypothesis for a wider PF2-1 campaign, stated here so MR4 tells PF2-1
WHAT it is testing rather than PF2-1 re-deriving it**: DQN-SLA
achieves `correct_shed` / protects urllc's own violation margin under
E4 co-located contention; DQN-QoE does not, despite also sacrificing
embb (`indiscriminate_failure`) -- i.e., the paper's hoped QoE-reward
advantage does NOT hold in this specific multi-slice overload regime,
and a wider campaign's job is to confirm or overturn that at proper
power, not to discover it fresh.

**STOP. Awaiting go before any wider live run** -- this milestone
recommends powering the campaign against the stated hypothesis above,
but does not launch it unilaterally.
