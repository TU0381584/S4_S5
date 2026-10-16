# M64/M65 pre-registration: Env B, AXIOM v2, MAPPO, and the resubmission campaign

Written and committed on 2026-10-16. This is after calibration and pilots on pilot seeds 2000 to 2009 only, and before any M64/M65 main-campaign result exists. Its git timestamp is the evidence. The seeds reported in the paper (900-929, 1000-1009) have not been run under any of the settings below.

## Why

A second-round internal review raised several problems:
1. Env A's optimum is a static rule: shed every mMTC request.
2. There was no published multi-agent RL baseline.
3. Graph attention had nothing to exploit.
4. The 19-gNB comparisons were underpowered.

M64 adds Env B to answer problems 1 and 3. It adds MAPPO for problem 2, and it raises the N=19 sample to 30 seeds for problem 4.

## Env B (coupled_dynamic_kpm_source.py), constants fixed now

Env B keeps Env A, with the shared PRB budget and per-episode backlog reset, and adds two mechanisms:
- Time-varying load: mean demand = 0.95 x nominal x m_i x (1 + 0.30 sin(2 pi (s + phi_i) / 60)). The phase phi_i is redrawn per gNB at every episode start.
- Inter-cell coupling: B_i(t) = 100 (1 - 0.15 x mean neighbour utilisation at t-1), over the same adjacency graph the encoder reads.

The reward weights are unchanged from Env A.

Calibration, on pilot seeds 2000-2002 using rules only, with N=3 fully connected and N=7 ring:
- The best adaptive rule beats the better trivial rule (static, accept-all) by 64% at N=3 and 14% at N=7.
- The static rule leaves URLLC at 39-54%; the adaptive rule keeps it at 97-98%.
- The adaptive rule also sheds eMBB under pressure.
- Neighbour-aware rules gain only 0.3-1.3% over local rules.

The attention question is therefore open, not built in. At N=19, per-slice compliance saturates, because a slice counts as compliant only when every gNB meets it. Env B is therefore run at N=3 and N=7 only, and the N=19 scaling evidence stays in Env A.

## AXIOM v2 (m64_axiom2.py), the only AXIOM from now on

The changes were chosen on Env B pilot seeds:
- Original AXIOM (LR 1e-4) learned only the static rule: 5.50, 5.51, and 6.10 on seeds 2000-2002.
- LR 1e-3 alone reached 8.61, 8.28, and 8.12.
- Adding a raw-feature skip into the per-slice heads reached 9.08, 8.46, and 9.06.
- On Env A pilot seeds 2000-2001, v2 matches the static oracle (12.88 vs 12.81, 12.53 vs 12.53).

v2 is the skip plus LR 1e-3, the same LR as the DQN baselines. The original AXIOM is also reported on Env B at N=3 for seeds 900-909, so the design change is visible.

The MLP ablation (axiom2_mlp) is v2 with the GAT encoder swapped for a per-node MLP; skip and LR are identical.

## Baselines

- Independent DQN and single-agent DQN, unchanged (LR 1e-3).
- MAPPO (m64_mappo.py): shared actor over own features plus context, centralised critic, PPO with GAE, the same 300 training episodes, and the same global reward. Settings were tuned only on pilot seeds 2000-2004, and they are fixed now:
  - actor LR 1e-3;
  - 10 epochs;
  - minibatch 64;
  - critic LR 1e-3;
  - clip 0.2;
  - entropy 0.01;
  - gamma 0.95;
  - GAE lambda 0.95.

  Untuned MAPPO collapsed to accept-all in 4 of 5 pilot seeds. The tuned version reached 6.0-8.5.
- Rules (m64_heuristics.py), all selected on training streams only:
  - static (shed all mMTC);
  - accept-all;
  - best local rule (own congestion, own priority queue, and eMBB shedding on the URLLC queue);
  - best neighbour-aware rule (adds mean neighbour congestion).

## Campaigns and seeds

All learned arms: 300 training episodes on stream = seed, then 50 evaluation episodes on stream 5000 + seed.

### Env B (M64), results in experiments/results/m64/

| Campaign | Seeds | Arms |
|---|---|---|
| N=3 fully connected | 900-929 | axiom2, axiom2_mlp, independent_dqn, single_agent_dqn, mappo_tuned, rule_static, rule_accept_all, rule_local, rule_neighbour |
| Original AXIOM, N=3 | 900-909 | axiom |
| AXIOM v2 sensitivity, N=3 | 900-909 | axiom2_lr3e-4, axiom2_lr3e-3, axiom2_wide |
| N=3 replication | 1000-1009 | axiom2, independent_dqn, single_agent_dqn, mappo_tuned, the four rules |
| N=7, three layouts (fully connected, ring, hex) | 900-911, 1000-1002 | axiom2, axiom2_mlp, independent_dqn, single_agent_dqn, mappo_tuned, the four rules |

### Env A (M65): AXIOM v2 rerun plus MAPPO, results in experiments/results/m65/

Baselines are reused from M63, since the same environment means the same baseline results.

| Campaign | Seeds | Arms |
|---|---|---|
| N=3 base | 900-929 | axiom2, axiom2_mlp, mappo_tuned |
| Replication | 1000-1009 | axiom2, mappo_tuned |
| Sensitivity (load102, load107, weights) | 900-909 | axiom2 |
| Federated (FedAvg sigma in {0, 0.5, 1, 2, 4}) | 900-909 | v2 |
| Federated replication (sigma 0) | 1000-1009 | v2 |
| FedProx (mu in {0.01, 0.1, 1}) | 900-902 | v2 |
| Disruption | primary and replication sets | full M4 rerun with v2 checkpoints |
| Scaling N=7, three layouts | 900-911, 1000-1002 | axiom2, mappo_tuned |
| Scaling N=19, three layouts | 900-911, 1000-1002, 912-926 (30 seeds) | axiom2, mappo_tuned |
| Scaling N=19 baselines, new seeds | 912-926 (seeds 900-911 and 1000-1002 reused from M63) | independent_dqn, single_agent_dqn |
| Attention ablation | 900-911 | axiom2_mlp at N=19 ring |

## Hypotheses and tests, fixed now

- Statistics: paired Wilcoxon signed-rank tests, Holm correction within each family, and 10,000-resample bootstrap CIs, as in M63.
- **H1, Env B N=3: AXIOM v2 beats both trivial rules.** Test the reward of AXIOM v2 against rule_static and rule_accept_all. Family size 2, one-sided in AXIOM's favour.
- **H2, Env B N=3 and N=7: AXIOM v2 against every learned baseline and the tuned rules.** Test AXIOM v2 against independent_dqn, single_agent_dqn, mappo_tuned, rule_local, and rule_neighbour, on reward and on per-slice SLA. Two-sided, with Holm per size.
- **H3, the primary attention test: AXIOM v2 against axiom2_mlp in Env B N=7, ring and hex.** Two-sided Wilcoxon on reward, Holm over the two layouts. A null or reversed result is reported as such, and the title drops "Graph-Attention" unless H3 favours attention.
- **H4, Env A N=19 (30 seeds per layout): AXIOM v2 against single_agent_dqn, independent_dqn, and mappo_tuned on priority-slice SLA.** Holm over 9 tests.
- **Screen:** the M63 validation screen rule is applied unchanged to every learned arm in M64 and M65.

Every result is reported, including any that weaken AXIOM.

## Addendum 1 (2026-10-16, 19:40), before any M64/M65 main result was read

**Problem.** Testing the screen on Env B pilot checkpoints (seeds 2000-2001, MAPPO) showed that its second criterion (fail if fewer than 90% of blocks target mMTC) is miscalibrated for Env B. In Env B the reward-optimal policy deliberately sheds eMBB under pressure, as the calibrated adaptive rule does, so a good policy can legitimately have an mMTC block share below 90%. The pilot MAPPO seed failed the screen with a reward of 7.50 and no collapse.

**Amendment, applying to Env B only.** The primary screen criterion is the first one alone: a checkpoint that blocks no request in its five greedy training-stream episodes is flagged as collapsed. The 90% criterion is still computed and reported in full for every arm, but no Env B claim rests on it.

**Unchanged.** For Env A (M65) the screen is applied exactly as pre-registered, with both criteria. No other part of the pre-registration changes.
