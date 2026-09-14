# M47-2-0 — lock the arm set before training (NO RIG)

M47-1 found static-at-cap ~= DQN-SLA and reframed the primary claim to
the three-way "learned admission control doesn't beat trivial, QoE
hurts." A single static reference is a weak control for that claim: a
reviewer can ask whether the scheduler favors urllc regardless of
where the ceiling sits (structural) or whether wide-open specifically
happened to coincide with what the scheduler wants (coincidental).
This gate adds a second, more discriminating non-learned reference and
resolves whether the existing non-ML baseline is redundant with
static-at-cap before any more time is spent.

## Second static reference: static-at-floor, not fixed-mid-band

Chose static-at-floor over fixed-mid-band because it is the more
discriminating test of the actual question. urllc's calibrated floor
(6 raw PRB) already clears the scheduler's hard `min_rbSize=5`
grant-eligibility guard (`gNB_scheduler_dlsch.c:1075`) by construction
-- M46-MR1's own derivation deliberately set the floor there, not
below it. That makes floor the tightest point on the calibrated band
that isn't itself broken by the scheduler-floor bug M41/M42 already
fixed:

- **If urllc is STILL protected pinned at its tightest calibrated
  point** (floor, not cap), that is STRONGER evidence for the
  structural claim than static-at-cap alone could ever provide --
  the scheduler would be shown to favor urllc across the ENTIRE
  calibrated range, not just at its most generous point.
- **If urllc instead fails at floor**, that shows the ceiling VALUE
  does matter, and static-at-cap's success in M47-1 is not just "any
  fixed policy works" -- a real, useful negative result either way.

A fixed-mid-band arm (e.g. pinned at `nominal_ratio=7`, MR1's own
existing design-choice value) would sit closer to cap than to floor on
embb's 5-10 band and wouldn't add much discriminating power beyond
what cap already tests -- floor is the more informative second point
given only one more arm is being added.

Built: `experiments/configs/m47/saclb_m47_static_at_floor.yaml`.
Identical to `saclb_m47_static_at_cap.yaml`
(`experiments/configs/m47/saclb_m47_static_at_cap.yaml`, M47-1) in
every field except `nominal_ratio`, which is set equal to
`min_ratio_floor` instead of `max_ratio_cap` for urllc (6, was 7) and
embb (5, was 7) -- `ceiling_step_ratio: 0` retained, same mechanism as
static-at-cap and Paper #4's own established static-at-cap arm.
mmtc's existing fixed point (floor==nominal==cap==5) unchanged.
Validated: loads cleanly, `nominal_ratio == min_ratio_floor` confirmed
for embb/urllc/mmtc, `ceiling_step_ratio == 0`.

## Is the non-ML baseline (`lb_only`) redundant with static-at-cap? No.

Read `lb_only_baseline.py`'s `LbOnlyHeuristic` and `mc_runner.py`'s
dispatch directly rather than assuming from the name:

- **Mechanism**: rejects a request if EITHER the request's own gNB is
  at/above `utilization_threshold` (0.97, whole-gNB aggregate) OR the
  request's own slice's observed `prb_used_ratio` is at/above
  `nominal_ratio/100 * capacity_margin` (default `capacity_margin=1.0`
  -- i.e., under MR1's config, rejects once a slice's OWN observed
  utilization reaches its `nominal_ratio` of 7%, for both urllc and
  embb). This is a REAL, per-step, state-REACTIVE rule -- not a fixed
  ceiling.
- **Confirmed it moves the ceiling through the exact same channel DQN
  does**: `mc_runner.py`'s `_select_actions()` calls
  `policy.decide(pending, cluster_state)` for `algorithm="lb_only"`,
  returning the same integer 0/1 action list DQN's `select_action()`
  produces, fed into the identical `env.step(actions)` ->
  `AdmissionGate.apply()` pipeline (accept raises the ceiling, reject
  lowers it, same `step_ratio`). static-at-cap's ceiling, by contrast,
  is structurally FROZEN (`ceiling_step_ratio: 0`) and cannot move
  regardless of any decision, observed or not.
- **No separate config needed**: `build_policy("lb_only", cfg)` takes
  whatever `cfg` is passed via `--config` (`saclb_m46_train.yaml`,
  same as the DQN arms) and `--algorithm lb_only` -- a policy choice,
  not a config difference. Nothing new to build for this arm.

**Verdict: genuinely distinct, not redundant.** `lb_only` is a
reactive, rule-based, quota-threshold admission heuristic that
actively moves the ceiling via the same mechanism a learned policy
would; static-at-cap/floor are structurally inert references that
never move at all. Per this gate's own instruction, the second static
reference is kept regardless of this finding, and now there is no
rig-time-forced-cut question either -- all 5 arms are mechanistically
distinct and worth keeping.

## GATE M47-2-0

**Final arm set for PF2-1c** (5 arms, all mechanistically distinct,
none redundant):

| arm | mechanism | config | training needed |
|---|---|---|---|
| DQN-QoE | learned, `reward_mode="qoe"` | `saclb_m46_train.yaml` | yes (M47-2-1) |
| DQN-SLA | learned, `reward_mode="sla"` | `saclb_m46_train.yaml` | yes (M47-2-1) |
| static-at-cap | frozen ceiling, `step_ratio=0`, pinned at cap | `experiments/configs/m47/saclb_m47_static_at_cap.yaml` (M47-1) | no |
| static-at-floor | frozen ceiling, `step_ratio=0`, pinned at floor | `experiments/configs/m47/saclb_m47_static_at_floor.yaml` (this gate) | no |
| non-ML baseline | reactive quota-threshold rule, `algorithm="lb_only"` | `saclb_m46_train.yaml` (policy flag only) | no |

`non-ML ≈ static-at-cap`: **no** -- confirmed mechanistically distinct
above, not merely asserted.

## STOP

Arm set locked, both new static configs built/validated (one from
M47-1, one from this gate), non-ML-vs-static-at-cap redundancy
question resolved (not redundant). Per this milestone's own gating,
awaiting go before M47-2-1 (offline training the two DQN arms' new
seeds -- the only arms that need training; all 3 non-learned arms are
ready to run as soon as PF2-1c starts).
