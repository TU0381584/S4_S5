# M110: per-gNB SLA compliance of the stored Env A policies (pre-registration)

Committed before any campaign run. This is the item of the pre-submission review that the stored logs could not answer, because they hold only cluster-level SLA flags.

## Question

The paper's priority-slice compliance counts a step only when every gNB meets the SLA. Does AXIOM's lead over the learned baselines in Env A at 19 and 37 gNBs also hold when compliance is measured per gNB?

## Design

- **No training.** Each stored checkpoint is loaded and evaluated again on its own held-out stream (50 episodes, stream 5000 + seed), at its own size and layout, by experiments/scripts/m110_pergnb.py.
- **Runs.** The 1,620 runs behind the Env A scaling figure, exactly as paper5_fig_scaling_trend.py pools them: AXIOM, DQN-SA, DQN-I and MAPPO at 3 gNBs (60 seeds), 7 gNBs (30 seeds under each of three layouts), 19 gNBs (60 under each of three layouts), and 37 gNBs (AXIOM on 60 hex, 30 ring and 30 fully connected seeds, each baseline on the 60 hex seeds). Stored and extension seeds are both included.
- **Recorder.** m75_run's per-gNB recorder (M75_PERGNB=1), already used for the Env B per-gNB figure. It applies the framework's per-gNB SLA test before the result is ORed over gNBs and changes nothing else.
- **Exactness.** Each re-evaluation must equal its stored evaluation exactly in reward, blocks and cluster-level SLA flags. A run that does not is reported and left out of the estimate. When it is exact the new log duplicates the stored one and is deleted, and per_gnb_sla.json and row.json are kept in experiments/results/m110/.
- **Static rule.** Not rerun. Per-gNB compliance is never below cluster-level compliance, and the rule's cluster-level value is already at least 99.97 %.

## Analysis (experiments/scripts/m110_analysis.py, committed with this file)

Per-gNB priority-slice compliance of a run is the mean over gNBs of the share of steps on which that gNB meets the SLA, averaged over URLLC and eMBB. For every size and policy the analysis reports its mean and 95 % bootstrap CI beside the cluster-level value. At each size AXIOM is compared with each learned baseline on the per-gNB measure with a two-sided Wilcoxon signed-rank test paired by layout and seed, ties within 1e-9 dropped, Holm-corrected over the three baselines.

## Predictions and what would change the paper

- The per-gNB values will be at least as high as the cluster-level values for every policy, and the gaps between policies will be smaller.
- **Decision rule.** At 19 and at 37 gNBs, AXIOM's lead over the closest learned baseline holds if it is at least 5 points with Holm p below 0.05. If it does not hold at either size, the paper must state that its scaling result depends on the cluster-level metric, and the claim is rewritten to match.
- Every result is reported whatever its outcome.

## Already seen

The harness was checked on seeds 900 and 11000 at 3 gNBs for all four policies and on seed 900 at 37 gNBs (hex) for AXIOM and DQN-SA, into a scratch directory. All ten re-evaluations were exact. Their per-gNB values were printed and are part of the campaign's runs, so these ten are not blind.

## Cost

About 36 s per run at 37 gNBs and under 7 s at 3 gNBs, so under 10 CPU-hours and under 2 hours at six parallel jobs.
