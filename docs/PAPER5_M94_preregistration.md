# M94: distilling AXIOM into a rule (pre-registration)

Committed on 2026-11-06, before any M94 probe, fit or rule evaluation whose result is reported. Gate D of the external review plan. Stored checkpoints only, no retraining, framework untouched. Every criterion is reported as HOLDS or FAILS, or as a flag. Runner: experiments/scripts/m94_distil.py. Analysis: experiments/scripts/m94_analysis.py, written after this commit and before any M94 result is read. Output: experiments/results/m94/.

## Feasibility (checked before this commit, not results)

- The distilled rule runs through mc_runner's no-learning path, exactly as the tuned rules do. To check that its feature extraction matches the framework, the tuned local rule (selected on training streams: shed every mMTC request, shed eMBB when the URLLC queue reaches 0.2) was re-expressed on the M94 features and run through the same path. On seeds 900 and 901 at 7 gNBs (ring) and 3 gNBs it reproduced the stored rule_local evaluations exactly (reward, blocks and SLA).
- The replay records AXIOM's decisions while running the stored checkpoint exactly as m64_run.eval_marl does. Held-out replays of seed 900 for all three targets and seed 901 for two reproduced the stored evaluations exactly. The congestion level was identical in every slice's slot of the node features at every step, so "congestion" is one well-defined per-gNB signal.
- These check outputs were discarded and every probe is rerun after this commit. scikit-learn 1.9.1 was installed for the trees, with numpy, SciPy, Matplotlib, PyTorch, PyYAML and pandas held at their versions.

## Targets

- B7_ring_900: AXIOM in Env B at 7 gNBs, ring layout, after 900 training episodes (m79/ep900_n7_ring, the checkpoints of Online Resource 1's longer-training table), seeds 900-911 and 1000-1002.
- B7_ring_300: the same cell after 300 episodes (m64/n7_ring), same seeds.
- B3: AXIOM in Env B at 3 gNBs, fully connected, the reported checkpoints (m64/n3_fully_connected), seeds 900-929.

## Data, features and model

- For each seed the checkpoint is replayed greedily for 50 episodes on its training stream (seed) and on its held-out stream (5000 + seed). Every actual request yields one example, with label 1 if AXIOM rejects it.
- Features of a request at gNB i for slice k: i's URLLC queue (queue_len_norm), i's congestion level (served PRBs over the budget, the signal the tuned rules read), slice k's PRB-used ratio at i, and the mean congestion level of i's neighbours in the layout. The plan's "own PRB-used ratio" is taken as the deciding slice's ratio, since the sum over slices equals the congestion level.
- One sklearn DecisionTreeClassifier per slice and seed (URLLC, eMBB and mMTC, so the rule decides every request), class_weight balanced, random_state 0, max_depth d. A slice whose training decisions are all one class gets a constant.
- Depth selection, on training-stream decisions only. For each d in {1, 2, 3}, fidelity is the 5-fold cross-validated agreement with AXIOM over all requests (KFold, shuffled, random_state 0), averaged over seeds. One depth per target is selected by the highest mean, with ties going to the shallower tree. Held-out streams are never used to choose anything.
- The selected depth's trees are refitted per seed on all of that seed's training-stream decisions.

## Endpoints and tests

- Held-out fidelity: agreement with AXIOM's decisions over all requests of the held-out replay, per seed, reported for every depth with the selected depth marked.
- Rule arm distilled_tree: the seed's trees run as a rule for 50 episodes on the seed's held-out stream.
- Per target, Holm over 4 tests. distilled_tree against AXIOM (the same checkpoint's stored evaluation) and against the tuned local rule (rule_local, tuned at those conditions, m64/n7_ring and m64/n3_fully_connected), on reward per step and on cluster-level priority-slice SLA. Paired by seed, two-sided Wilcoxon signed-rank (zero_method wilcox), with bootstrap 95% CIs of the mean difference (10,000 resamples, default_rng(0)).
- Extracted thresholds, reported only. The splits of every eMBB tree, the number of seeds whose eMBB tree splits on the URLLC queue, and the median of those URLLC-queue thresholds against the tuned rule's 0.2.

## Stop conditions

- D-S1. If a target's mean held-out fidelity at its selected depth is below 0.80, flag NOT-DISTILLABLE for that target. It is reported in Online Resource 1 only, with no main-text claim.
- D-S2. If distilled_tree beats AXIOM on reward with Holm-adjusted p < 0.05 for any target, STOP and report, because this changes the framing.

## Budget

About 0.25 CPU-hours: 120 replays of 50 episodes (6 s at 7 gNBs, 3 s at 3 gNBs) and 60 rule evaluations. At most 5 parallel jobs, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1.
