# M43-P1B-1: offline ceiling-trajectory replay, all 28 submitted seeds

No rig. Reused `experiments/scripts/live_scale_offline_env.py` (existing,
heavily-precedented across this project's M1-M7 history — not a new
simulator), which defaults to `experiments/configs/saclb_campaign_v2.yaml`
(the same config the real live campaign used) with `ClosedLoopKpmSource` at
its own default `backlog_capacity=200` and real live-observed
`MEAN_OFFERED_RATIO` — chosen over the checkpoint's own `*_offline_train.yaml`
training environment (Lmax=1000/backlog_capacity=2000, a more forgiving
regime meant to help learning) since this replay's purpose is predicting
live behavior, not reproducing training dynamics.

New script: `experiments/scripts/m43_p1b_offline_replay.py`. One correctness
detail worth flagging: `mc_runner.run_mc()`'s own internal seed arithmetic
(`seed = base_seed + rep`) does NOT match what the real campaign used
(`run_live_eval_arm.py`'s `batch_seed = args.seed * 1000 + batch_idx`,
confirmed by reading `saclb_xapp.py` directly — it threads `args.seed`
identically into both `RANEnv(seed=...)` and `run_single(seed=...)`). This
script calls `run_single()` directly in its own loop with the correct
`batch_seed = base_seed*1000 + 0` (matching each seed's real first/only
replayed batch) rather than using `run_mc()`'s convenience wrapper.

Config: DQN-QoE arm, the submitted checkpoint, all 28 submitted seeds
(950-977), 2 episodes each (matching the real campaign's own batch size and
M43-P1's own live test scope).

## Result: `experiments/results/m43_p1b/seed_trajectory_matrix.csv`

| Slice | FLOOR-PINNED | MIXED | CAP-RIDING |
|---|---|---|---|
| urllc | **28/28 (100%)** | 0 | 0 |
| mmtc | **28/28 (100%)** | 0 | 0 |
| embb | 0 | 4/28 | 24/28 |

**urllc and mmtc are FLOOR-PINNED (>=80% of steps with ceiling raw PRBs < 5)
for every single one of the 28 actual submitted seeds, with zero
exceptions** — in every seed's replay, 100% of steps (120/120) had both
slices' ceiling below the scheduler's hard floor. embb never floor-pins
(ranges 4.2%-24.2% of steps below floor across seeds, always classified
CAP-RIDING or MIXED).

**This is not actually surprising once traced to its cause, and reconciles
a piece of P1's own open question**: urllc's configured range is
`min_ratio_floor=1%` through `max_ratio_cap=4%` (raw PRBs 1 through 4) and
mmtc's is `1%` through `3%` (1 through 3) — per M42's own static audit,
**neither slice's cap alone ever reaches 5 raw PRBs, so no policy decision
within their legal range can ever clear the scheduler floor.** Whether the
policy pins a slice at its floor (as P1's own live test, seed 43003, showed)
or rides it up to its cap (as the one historical sample checked in M42,
seed 961, showed: `max_ratio=4` for urllc, `max_ratio=3` for mmtc) is
irrelevant to the outcome — both extremes are equally below 5. **The
apparent disagreement between P1's seed 43003 and M42's seed-961 sample was
never a disagreement about whether the mechanism fires — both are
uniformly, deterministically broken for urllc/mmtc regardless of where in
their range the policy sits.**

## GATE P1B-1 — the load-bearing number

**28/28 (100%) of the actual submitted seeds have urllc and mmtc
floor-pinned for their entire configured range, for the full evaluated
window.** This is not a probabilistic, seed-dependent phenomenon for these
two slices — it is a deterministic consequence of the config's own numbers,
confirmed to hold uniformly across every seed actually used in the
submitted campaign.

**Adaptation needed for P1B-2's "pick the two extremes" instruction**:
urllc/mmtc show zero variance to pick extremes from (all 28 seeds identical:
100% floor-pinned). The only axis with real seed-dependent spread is embb
(4.2% at seed 961, the closest thing to a "best case," to 24.2% at seed 960,
the "worst case" for embb specifically — though embb itself never
floor-pins at all). Recommend, pending confirmation before proceeding:
P1B-2 live-tests seed 961 (lowest embb exposure — the closest this campaign
gets to a "healthy" seed on any axis) and seed 960 (highest embb exposure)
as the two genuinely distinguishing extremes, since urllc/mmtc's own
100%-uniform prediction means any seed is equally representative for them
specifically. Awaiting go before proceeding to the live P1B-2 test with this
seed pair (or an alternative pair, if a different selection is preferred).
