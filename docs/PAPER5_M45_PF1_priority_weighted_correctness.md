# M45-PF1 — the priority-weighted correctness metric

## Status: NO RIG. Analysis + code only, validated against M44-E4's
## already-collected co-located trajectory data (6 combinations,
## already on disk, no new live time spent). GATE PF1.

## 0. Why not the existing compliance signals

`sla_compliance_all_slices` (`reward.py::check_violations` /
`ViolationCheck`) is P0-blind by construction: a slice receiving ZERO
PRB grants shows `dl_errors=0, dl_bler=0` (nothing attempted, nothing
to fail), so `queue_violation`/`loss_violation` both read false and the
slice is scored "compliant" while fully starved. This is not a
tightenable threshold problem -- the signal literally cannot see the
failure mode this entire M44 series has been characterizing (RLC AM
admission rejection under contention). M35's metric is excluded per
this milestone's own standing instruction (flagged untrustworthy
separately from P0).

Critically, `compute_qoe_reward` (the DQN-QoE arm's own reward) is
**not immune to this either**: its `sla_viol` term is computed from the
exact same `ViolationCheck.margin`, so it shares the same blind spot by
construction. An external judge built from either reward's own machinery
would not be independent of what it's judging. The metric below uses
neither.

## 1. The metric

Built entirely from the radio-layer instruments this project
established as real and load-bearing (M43's RLC AM instrumentation,
the corrected iperf3 throughput parser, M44-E2b's M41DBG scheduler
state) -- none of which either reward function consumes. For each
co-located slice k in {urllc, embb} (mmtc excluded, per E1b: no
realistic band) and each sample window t:

```
C_k(t) = clip(served_k(t) / offered_k(t), 0, 1) * (1 - rlc_reject_frac_k(t))
```

- `served_k(t)/offered_k(t)`: real delivered-vs-offered throughput
  fraction, from the corrected `parse_recent_intervals` (handles
  bare-"0.00" zero-rate lines correctly -- the M44-C bug that would
  otherwise silently mask exactly this kind of total outage).
- `rlc_reject_frac_k(t)`: fraction of SDUs the RLC AM entity actually
  rejected at its `tx_maxsize` admission gate this window, from the
  M43DBG `rlc_am_recv_sdu` instrumentation, entity resolved per-slice
  via the genuine NSSAI/rnti correlation method from M44-E4 (not a
  busiest-entity heuristic).

The product form matters: a slice can briefly show adequate throughput
while its RLC buffer is already saturating (the M44-C bufferbloat
finding -- served traffic can lag the real admission-layer distress by
tens of seconds), so multiplying rather than averaging the two terms
means genuine admission-layer failure drags the score down even before
it fully shows up in delivered throughput.

**Cross-slice, priority-weighted score for window t:**

```
Score(t) = (w_urllc * C_urllc(t) + w_embb * C_embb(t)) / (w_urllc + w_embb)
```

with `w_urllc = 5.0`, `w_embb = 3.5` -- these are not new numbers: they
are `priority_weight` (omega_k in papers #1/#2's own eq.2) read
directly from the submitted, frozen `saclb_campaign_v2.yaml`
(`slices[urllc].priority_weight = 5.0`, the highest of the three
configured slices; `slices[embb].priority_weight = 3.5`). Normalizing
by the weight sum keeps `Score(t) in [0,1]` (0 = total cross-slice
failure, 1 = perfect service to both), while the weighting still makes
urllc's health dominate: a policy that sacrifices embb to protect
urllc scores high (urllc's near-1 `C_urllc` carries weight 5.0 even
against a near-0 `C_embb`); a policy that lets urllc suffer to keep
embb comfortable scores low (urllc's poor `C_urllc` is weighted 5.0,
dragging the average down hard regardless of embb's state). This is
the intended asymmetry: "protect urllc under contention, shed embb if
something has to give."

**Episode/run-level metric ("PWC"):** the mean of `Score(t)` over the
run's sampling windows (the same >=120s hold / ~15s cadence / 8-sample
convention used throughout M44).

## 2. Why this is provably sensitive to the starvation P0 found

A fully-starved slice (the exact P0/M44-C failure mode) shows
`served/offered -> 0` **and** `rlc_reject_frac -> 1` simultaneously --
both terms of `C_k` collapse to 0 by construction, driving that slice's
contribution to `Score(t)` to 0 regardless of its priority weight.
`sla_compliance_all_slices` reads the identical scenario as 100%
compliant (P0's own finding). The two signals are structurally
opposite on the exact case that matters; this is not a difference of
degree.

## 3. Mapping to DQN-QoE's own objective (interpretability, not circularity)

`compute_qoe_reward`'s formula is `r_t = alpha*MOS_norm - beta*cost -
gamma*sla_viol` (submitted weights: alpha=1.0, beta=0.2, gamma=0.5).
Notably, **this reward has no explicit per-slice priority weight at
all** -- `mean_mos` averages every slice's QoE-mapper MOS equally
(`sum(mos_values)/len(mos_values)`), unlike `compute_step_reward`'s
(the SLA arm's) `service_term`, which explicitly multiplies by
`spec.priority_weight` per slice. So the campaign's real empirical
question is well-posed and non-circular either way it comes out:

- If DQN-QoE (trained on an *unweighted*-average MOS objective) still
  achieves a *higher* PWC than DQN-SLA (trained with explicit
  `priority_weight`s baked into its reward), that is a genuine,
  interpretable finding -- QoE-shaped training produces better
  real-world prioritization behavior *despite* not being told to
  prioritize explicitly, plausibly because urllc's QoE-mapper curve
  (tighter loss/latency budgets, per its own `saclb_campaign_v2.yaml`
  spec) punishes urllc degradation more steeply in MOS terms than
  embb's.
- If DQN-SLA wins instead, that is equally interpretable: its explicit
  weight signal translated into better real prioritization, as
  designed.

Either outcome is meaningful because PWC's own priority weights
(`w_urllc=5.0`, `w_embb=3.5`) are the framework's *definition* of what
"correct prioritization" means, taken directly from the submission
record -- not derived from either reward function's live computation,
and not fed as an input to either policy's training. The judge and the
two candidates being judged are independent by construction.

## 4. Code

`experiments/scripts/m45_priority_weighted_correctness.py` implements
`compute_c_k`, `compute_score`, and `compute_pwc_for_run` (reads the
same per-slice trajectory JSONL schema M44-D/E1b/E2b/E4 already use --
`{slice}_served_kbps`, `{slice}_offered_kbps`, `{slice}_rlc_rej_pct`)
with `W_URLLC=5.0, W_EMBB=3.5` as module constants sourced from
`saclb_campaign_v2.yaml`, cited inline. No new live data -- reused
directly against M44-E4's own 6 already-collected trajectory files as
a worked validation (no rig time spent).

## 5. Validation against M44-E4's own already-collected data

Applying PWC to the 6 co-located (urllc_ceiling, embb_ceiling) runs
already on disk from M44-E4 (see `pf1_validation.jsonl` for the full
per-run breakdown):

| urllc_ceil | embb_ceil | mean C_urllc | mean C_embb | PWC |
|---|---|---|---|---|
| 6 | 7 | 0.421 | 0.100 | 0.289 |
| 7 | 7 | 0.871 | 0.125 | 0.564 |
| 8 | 7 | 0.756 | 0.090 | 0.482 |
| 7 | 5 | 0.857 | 0.063 | 0.530 |
| 7 | 8 | 0.866 | 0.156 | 0.573 |
| 7 | 10 | 0.830 | 0.234 | 0.585 |

(computed by the script directly against M44-E4's own trajectory
files, written to `pf1_validation.jsonl`; these are the actual values,
not illustrative -- regenerate via the script if the underlying
trajectory files ever change.)

The metric behaves as intended: raising urllc's ceiling 6->7 (embb
fixed at 7) moves PWC by +0.275 (0.289->0.564), while raising embb's
ceiling all the way from 5 to 10 (urllc fixed at 7) moves PWC by only
+0.055 (0.530->0.585) -- despite embb's own `mean_C_embb` nearly
quadrupling (0.063->0.234) over that same range. PWC is dominated by
urllc's state, exactly the "protect urllc, shed embb" asymmetry the
weighting was designed to express, and this is directly visible from
already-collected data without spending any new rig time.

## 6. What has NOT been done
- No live pilot -- that is PF2.
- The exact per-run numbers in section 5's table should be read from
  `pf1_validation.jsonl`, generated by the script, not retyped by hand
  in future citations of this doc.

## GATE PF1

Reporting the metric definition and its sensitivity/interpretability
argument now. Awaiting go before PF2 (the live pilot).
