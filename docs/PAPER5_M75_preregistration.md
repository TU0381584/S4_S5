# M75: fourth-review runs (pre-registration)

Committed on 2026-10-22, before any M75 run. These runs answer the fourth internal review: (1) the scaling evidence comes only from Env A, where a fixed rule is near-optimal, and (2) at 37 gNBs the DQN baselines that do not collapse keep less priority-slice compliance than policies that accept every request, which suggests under-tuned baselines. Every check is reported whether it holds or fails, and nothing here replaces a reported result. Runner: experiments/scripts/m75_run.py, a wrapper over m73_run.py and m64_run.py; the framework is not modified. Output goes to experiments/results/m75/.

The wrapper was checked before this plan was committed. With per-gNB recording on, an Env B rule evaluation at three gNBs reproduced the stored log exactly, and the learning-rate and minibatch overrides reach the single-agent and independent DQNs only, never AXIOM.

## B. Accept-all as a reference at scale (reported only)

- Env A, rule_accept_all, at 7 gNBs (seeds 900-911, 1000-1002), 19 and 37 gNBs (seeds 900-926, 1000-1002). The rule and the simulator never read the layout in Env A, so each size runs once, in the hex cell.
- Reported: priority-slice compliance and reward at each size, and which learned arms fall below it.

## C. DQN baselines tuned at 19 and 37 gNBs (Env A)

- Grid, per arm (single-agent DQN, seeded as in M73, and independent DQN) and per size (19 and 37 gNBs): learning rate {1e-4, 3e-4, 1e-3} x minibatch {16, 64}, 6 configurations. Training stays at 300 episodes, every other setting unchanged. The current setting is 1e-3 and 16.
- Pilot seeds 2000-2004, hex layout, evaluated on streams 7000-7004 as in every earlier pilot. Selection: the configuration with the highest mean pilot reward per arm and size; a tie goes to the current setting.
- Confirmation: each selected configuration other than the current one is retrained on seeds 900-926 and 1000-1002 on the hex layout and compared with the stored AXIOM results on the same seeds (m65_scaling/n19_hex, m73/A_n37_hex). Where the current setting is selected, the stored baseline results stand and are used.
- C1. AXIOM beats each tuned baseline on priority-slice compliance and on reward at both sizes. Holm over these 8 tests, each adjusted p < 0.05 with AXIOM ahead.
- Reported: the full pilot grid, and whether any tuned baseline exceeds accept-all.

## D. Env B at 19 gNBs with a per-gNB compliance metric

- Env B as in M64, 19 gNBs, hex layout, seeds 900-911 and 1000-1002 (15 seeds, as at seven gNBs). Arms: AXIOM v2, single-agent DQN (seeded), independent DQN, MAPPO (mappo_tuned), and the rules rule_static, rule_accept_all and rule_local_transfer. The last applies, without re-tuning, the local rule selected on training streams at seven gNBs, which is also the rule selected at three gNBs (shed every mMTC request, shed eMBB when the URLLC queue passes 0.2).
- Per-gNB priority-slice compliance: for each evaluation step and each gNB, URLLC (eMBB) counts as compliant if that gNB meets its SLA under exactly the framework's own per-gNB test; the metric is the mean over steps and gNBs, averaged over URLLC and eMBB. The existing cluster-level compliance requires every gNB to comply at once and is reported alongside. The training reward is unchanged; note that its violation penalty also ORs over gNBs.
- D1. AXIOM beats the single-agent DQN, the independent DQN and MAPPO on reward and on per-gNB priority-slice compliance. Holm over these 6 tests, each adjusted p < 0.05 with AXIOM ahead.
- D2. AXIOM beats rule_static and rule_accept_all on reward. Holm over these 2 tests, adjusted p < 0.05.
- Reported: AXIOM against rule_local_transfer on reward and per-gNB compliance, and cluster-level compliance for every arm.

## E. Descriptive additions (not confirmatory)

- The pre-registered validation screen applied to the M73 checkpoints at 37 gNBs, reported as pass counts.
