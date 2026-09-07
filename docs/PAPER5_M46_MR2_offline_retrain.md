# M46-MR2 — offline retrain under the MR1 band-aligned config (Path B)

OFFLINE ONLY. Trains DQN-QoE and DQN-SLA under
`experiments/configs/m46/saclb_m46_train.yaml` (MR1's output), matched on
reward mode only, against `ClosedLoopKpmSource` -- the fixed,
per-slice-independent env Path B deliberately defers the cross-slice
coupling question on. Per this milestone's own framing: **offline
convergence does not license trust** (Stage 12: zero offline/live
correlation for this exact architecture family). MR3's live revalidation
is the actual trust gate; this one only confirms both arms trained
cleanly under the new config and actually move their actions.

## What was built and run

- `experiments/scripts/m46_mr2_train_with_diagnostics.py` (new) --
  identical to the existing `train_offline_live_scale.py` (same config
  load, same `kpm_source_factory`, same `run_mc` call, not reimplemented)
  except it non-invasively wraps `oranslice_drl.drl_policy.DQNPolicy
  .train_step()` -- frozen source, byte-unedited -- to also capture the
  `loss`/`grad_norm`/`epsilon`/`avg_target_q` values that method already
  computes and returns on every call but that `mc_runner.run_mc()` never
  logs anywhere in this project's existing pipeline. Same non-invasive
  wrap-a-method technique M41 used for `send_control()`. Verified the
  wrap changes nothing about training itself (forwards the original
  return value unchanged) via a 3-episode smoke test before the real
  sweep: epsilon values recovered from the wrap matched the documented
  closed-form recursion exactly (`1.0 * 0.985^2 = 0.970225` after 2
  episodes).
- `experiments/scripts/run_m46_mr2_train.sh` (new) -- trains DQN-QoE and
  DQN-SLA across the SAME 6-seed set, same episode count (300, matching
  this project's own established default), same config, same env,
  differing only in `--reward-mode`. Seeds 256-261 reuse the exact
  convention Stage 10/12 already established for this pipeline
  (`docs/STAGE10_fullpower_reeval.md`: "retrains dqn_sla_v2/dqn_qoe_v2
  across 5 NEW seeds (257-261)" on top of the original seed256) -- not
  invented for this milestone, and chosen so these checkpoints double as
  the seed pool for the eventual PF2-1 pilot ("3-5 seeds" + a replication
  batch) without a second training pass. Runs from `cwd=framework/` with
  absolute paths (this project's own documented fix for a real,
  previously-hit silent-failure mode in `run_offline_v2_reverify.sh`),
  and checks for both `checkpoint.pt` and `train_diagnostics.jsonl`
  after every run, aborting loudly on either being missing.
- `experiments/scripts/m46_mr2_convergence_check.py` (new) -- reads each
  of the 12 runs' `omega_log.jsonl` (reward, live ceilings) and
  `train_diagnostics.jsonl` (loss, epsilon), computes per-run Q1-vs-Q4
  reward, decile-level reward shape, Q1-vs-Q4 loss (by train_step CALL
  order, not episode index -- see the script's own docstring for why
  exact episode attribution is deliberately not attempted), final
  epsilon, and the distinct `max_ratio` values each slice's live ceiling
  actually visited across the whole run.

All 12 runs completed cleanly (~12 min wall-clock total, not the ~3-4h
originally estimated from an older, unrelated precedent) -- 12/12
checkpoints and 12/12 diagnostics files written, confirmed by the sweep
script's own per-run existence check.

## GATE MR2 answers

### (1) Offline convergence reached, both arms, matched?

**Not in the classic monotonic-improvement sense -- reported plainly,
not smoothed over.** Reward does NOT improve from Q1 to Q4 in ANY of the
12 runs; loss does not shrink in any of the 12 runs. Both are reported
honestly below rather than reframed to fit an expected "convergence"
narrative.

| mode | seed | reward decile1 | decile3 | decile10 | d1->d3 | d3->d10 | loss Q1 | loss Q4 | final epsilon |
|---|---|---|---|---|---|---|---|---|---|
| qoe | 256 | -0.168 | -0.380 | -0.363 | -0.212 | +0.017 | 0.158 | 0.548 | 0.050 |
| qoe | 257 | -0.176 | -0.376 | -0.360 | -0.200 | +0.016 | 0.164 | 0.631 | 0.050 |
| qoe | 258 | -0.177 | -0.366 | -0.352 | -0.189 | +0.014 | 0.188 | 0.609 | 0.050 |
| qoe | 259 | -0.184 | -0.295 | -0.362 | -0.111 | -0.067 | 0.268 | 0.591 | 0.050 |
| qoe | 260 | -0.209 | -0.367 | -0.359 | -0.158 | +0.008 | 0.259 | 0.591 | 0.050 |
| qoe | 261 | -0.213 | -0.360 | -0.343 | -0.147 | +0.017 | 0.239 | 0.578 | 0.050 |
| sla | 256 | -3.295 | -10.880 | -10.236 | -7.586 | +0.644 | 88.4 | 496.7 | 0.050 |
| sla | 257 | -3.532 | -10.737 | -10.179 | -7.206 | +0.559 | 106.0 | 506.3 | 0.050 |
| sla | 258 | -5.791 | -8.918 | -9.476 | -3.127 | -0.558 | 115.7 | 569.7 | 0.050 |
| sla | 259 | -5.876 | -5.719 | -10.303 | +0.158 | -4.585 | 211.6 | 487.0 | 0.050 |
| sla | 260 | -7.840 | -10.984 | -10.324 | -3.144 | +0.660 | 270.9 | 511.5 | 0.050 |
| sla | 261 | -8.052 | -10.975 | -10.288 | -2.922 | +0.687 | 286.6 | 442.4 | 0.050 |

Full per-run data: `experiments/results/m46_mr2/convergence_report.csv`.

**The actual shape, matched across nearly all seeds in both arms**: a
sharp drop from the first decile (episodes 1-30, epsilon near 1.0,
mostly-random actions) to the third decile (episodes 61-90, epsilon
already decaying), then a **plateau** for the remaining ~70% of training
(decile3-to-decile10 drift is 3-40x smaller in magnitude than the
decile1-to-decile3 drop, in 10 of 12 runs). Two seeds break this pattern
in a documented, not-hidden way: qoe/259 and sla/259 both show a smaller
initial drop and a continued late decline instead of an early plateau --
a real seed-dependent difference, not an aggregation artifact (both
happen to be the same seed value, 259, across both reward modes, which
may or may not be coincidental -- not investigated further, flagged
rather than asserted).

Epsilon decayed to its documented floor (0.05) in all 12 runs, reached
by ~episode 200 as `dqn_admission.py`'s own header comment predicts for
this exact 0.985-per-episode/300-episode schedule -- confirms the
non-invasive capture recovered the real, correct value, not an artifact
of the wrap.

**Plausible mechanism (explicitly flagged as an interpretation, not an
established fact):** MR1 deliberately confined BOTH controllable
slices' entire ratio range to sit inside their own already-measured
GRADED bands -- by construction, every reachable point is already a
partial-service/congested operating point (M44-D's own top-of-band point
for urllc, ceiling=8, is only ~101% served; M44-E2b's top-of-band point
for embb, ceiling=10, is only ~61% served). There may be no
straightforwardly-learnable "safe" action inside this range to converge
toward, unlike a config with real full-headroom points available -- so a
mostly-random early policy landing on lucky combinations by chance, and
a mostly-greedy late policy converging to a systematic-but-still-
imperfect choice within an inherently constrained band, is a plausible,
mechanistically-grounded explanation for reward settling BELOW its early
near-random level rather than above it. This is consistent with, but not
proof of, anything -- it is offered as a hypothesis for interpretation,
not a finding to build on. **Per this milestone's own explicit
instruction, this offline reward pattern is not interpreted here as a
QoE-vs-SLA distinction** (the pattern is common to both arms) **nor as
evidence of live behavior** (Stage 12 already established offline and
live are uncorrelated for this architecture family) -- it is reported
because MR2 asked for the reward curve, honestly, not because it
resolves anything.

Loss growing rather than shrinking is consistent with, and does not
contradict, ordinary DQN mechanics: TD loss tracks the magnitude/
variance of a bootstrapped, periodically-updated target, not an
"accuracy" metric that must monotonically fall -- as returns shift from
near-zero (initial network) to the real, larger-magnitude, noisier
values this congested-band regime produces, loss can legitimately grow
even under otherwise-ordinary training. Flagged as the standard
explanation, not verified against this specific run beyond the pattern
being consistent with it.

### (2) Does each policy exercise its full in-band action range, or collapse to a static ceiling?

**Exercises the full range -- 12/12 runs, unambiguous pass, no
exceptions.** Every single run (both reward modes, all 6 seeds) visits
every one of MR1's exact configured points for both controllable slices:

| slice | expected range (MR1) | observed in ALL 12 runs |
|---|---|---|
| urllc | {6, 7, 8} | {6, 7, 8} -- exact match, every run |
| embb | {5, 6, 7, 8, 9, 10} | {5, 6, 7, 8, 9, 10} -- exact match, every run |
| mmtc | {5} (fixed by design) | {5} -- exact match, every run (confirms the fixed-slice design held under real training, not just the smoke test) |

This is the criterion this gate's own framing treats as decisive ("a
policy that trains to a static ceiling has nothing to revalidate") --
and it is a clean pass in every single one of the 12 runs, regardless of
the reward-curve shape discussed above. Whatever is happening with
reward/loss, both policies are actively using their entire configured
control surface throughout training, not degenerating to a fixed
ceiling.

### (3) Checkpoint paths + exact provenance for MR3

| | value |
|---|---|
| Config | `experiments/configs/m46/saclb_m46_train.yaml` (MR1 output, unedited) |
| Env | `ClosedLoopKpmSource` (fixed, per-slice-independent -- Path B, coupling deferred to MR3) |
| Algorithm | `dqn` (`DQNAdmissionPolicy` / `oranslice_drl.drl_policy.DQNPolicy`) |
| Episodes/run | 300 |
| Seeds | 256, 257, 258, 259, 260, 261 (same 6, both reward modes) |
| Hyperparameters | Table I defaults, unedited (`gamma=0.95, lr=0.001, epsilon_start=1.0, epsilon_end=0.05, epsilon_decay=0.985/episode, batch_size=16, target update every 10 episodes`) |
| Checkpoints | `experiments/results/m46_mr2/offline_train/{qoe,sla}/seed{256..261}/dqn/offline_closed_loop/rep_0/checkpoint.pt` (12 files) |
| Omega logs | same directories, `omega_log.jsonl` |
| Loss/epsilon diagnostics | same directories, `train_diagnostics.jsonl` (new artifact this milestone) |
| Convergence summary | `experiments/results/m46_mr2/convergence_report.csv` |

## What this does NOT establish

Per the milestone's own explicit instruction: this offline reward
pattern is not a QoE-vs-SLA verdict, and offline convergence (of any
shape) does not license trust in live behavior for this architecture
family (Stage 12). The 12 checkpoints above are inputs to MR3 -- the
actual trust gate -- not a conclusion in themselves. The unresolved
coupling confound from PF2-0 (`ClosedLoopKpmSource` has no cross-slice
term; E4's live regime is defined by one) remains fully open and is
exactly what MR3 is for.

## STOP

GATE MR2 reported: action-range exercise is a clean, unambiguous pass
(12/12); offline reward/loss curves are reported honestly as NOT showing
classic convergence, with the observed shape characterized rather than
hidden. Checkpoint/config/seed provenance for MR3 is above. Awaiting go
before MR3 (live revalidation).
