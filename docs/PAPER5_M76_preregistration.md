# M76: fifth-review runs (pre-registration)

Committed on 2026-10-23, before any M76 run. These runs answer the fifth internal review: (1) when would AXIOM be preferred to a rule, (2) the reward's SLA penalty does not scale with the cluster, (4) no published cooperative baseline, (5) Env A is only about 5% oversubscribed. Every check is reported whether it holds or fails, and nothing here replaces a reported result. Runners: experiments/scripts/m76_run.py and m76_shift.py, wrappers over m75_run.py, m73_run.py and m64_run.py; the framework is not modified. Output goes to experiments/results/m76/. Per-gNB compliance (M75) is recorded in every Env B cell.

Checked before this commit: m76_shift.py under nominal load reproduces the stored M75 logs and per-gNB records exactly (seed 900, all three arms); the per-gNB penalty satisfies new reward = old reward + cluster penalty - per-gNB penalty on every step tested (mean penalty at 19 gNBs under the static rule 57.9 against 10.9); the heterogeneous multipliers and the Env A load factor take effect; the VDN arm trains.

## b1. Load shift at nineteen gNBs (Env B)

- The 15 AXIOM checkpoints of M75 D (seeds 900-911, 1000-1002, hex) and the local rule tuned at seven gNBs, plus the static rule, are evaluated without retraining or re-tuning under 1.10, 1.15 and 1.20 times the nominal load, as M72 did at three gNBs.
- B1. AXIOM beats the carried-over tuned rule on reward at all three loads, Holm over 3, adjusted p < 0.05.
- Reported: per-gNB compliance, the static rule, and the nominal condition.

## b2. Heterogeneous per-gNB load (Env B, seven gNBs, ring)

- Each gNB's load multiplier is drawn from U[0.75, 1.25] per seed (the reported Env B uses U[0.9, 1.0]). Every arm trains and is evaluated under this heterogeneity: AXIOM, single-agent DQN (seeded), independent DQN, MAPPO, rule_static, rule_accept_all, rule_local_transfer (the nominally tuned rule, not re-tuned), and rule_local re-tuned on the heterogeneous training streams exactly as the original tuning was done. Seeds 900-911, 1000-1002.
- B2. AXIOM beats the nominally tuned rule on reward, adjusted p < 0.05 (single test).
- Reported: AXIOM against the re-tuned rule and the learned baselines, per-gNB compliance.

## c. Per-gNB SLA penalty (Env B, nineteen gNBs, hex)

- The reward's violation penalty is charged per violating gNB (sum over gNBs) instead of once per slice for the cluster. Every arm trains and is evaluated under it: AXIOM, single-agent DQN (seeded), independent DQN, MAPPO, rule_static, rule_accept_all, rule_local_transfer. Seeds 900-911, 1000-1002.
- C1. AXIOM trained with the per-gNB penalty keeps higher per-gNB priority-slice compliance than AXIOM trained with the original reward (M75 D, same seeds), paired, p < 0.05.
- C2. AXIOM with the per-gNB penalty beats the static rule on per-gNB priority-slice compliance, p < 0.05.
- Reported: AXIOM against the learned baselines and the tuned rule under the new reward.

## d. VDN baseline

- Value-decomposition network over the independent DQN's per-gNB networks (identical networks and schedule, joint summed TD target, Sunehag et al., AAMAS 2018), no tuning. Cells: Env A three gNBs (seeds 900-929), Env B three gNBs (seeds 900-929), Env A nineteen gNBs hex (seeds 900-926, 1000-1002), each against the stored AXIOM results on the same seeds.
- D1. AXIOM beats VDN on reward in all three cells and on priority-slice compliance at nineteen gNBs, Holm over these 4 tests, adjusted p < 0.05.
- Reported: priority-slice compliance at three gNBs, collapse counts.

## e. Oversubscription (Env A, nineteen gNBs, hex)

- Mean offered demand at 1.10 and 1.20 times each slice's nominal share (reported Env A uses 1.05). At 1.10 the URLLC and eMBB demand sits at their PRB caps; at 1.20 it exceeds them, so no policy can keep those slices' SLAs throughout. Arms: AXIOM, single-agent DQN (seeded), independent DQN, MAPPO, rule_static, rule_accept_all, all retrained under each load. Seeds 900-911, 1000-1002.
- E1. AXIOM beats each learned baseline on priority-slice compliance at both loads, Holm over 6, adjusted p < 0.05.
- Reported: reward, the static rule and accept-all at each load.

## Results (campaign 14:17 on 2026-10-23 to 00:51 on 2026-10-24; analysis in experiments/results/m76/analysis.json)

All 353 jobs exited cleanly. 2 of 6 predictions hold; B2, C1, C2 and D1 fail. Every result is reported in the manuscript and in S17 of Online Resource 1.

- **B1 holds.** At 19 gNBs under 110/115/120% load AXIOM earns 6.23, 7.55 and 8.67 more reward per step than the carried-over tuned rule, 14 of 15 seeds each, Holm p = 0.0004. But the tuned rule keeps 12 to 15 points more per-gNB compliance (it sheds eMBB), and the static rule earns 1.8 to 2.0 more reward than AXIOM, which makes the static rule's decisions in 9 to 11 of 15 seeds. Nominal reproduces M75 D exactly.
- **B2 fails.** Uneven per-gNB load (U[0.75,1.25], 7 gNBs ring): AXIOM +0.36 over the nominally tuned rule (9/15, p 0.23); ties the re-tuned rule (+0.05); the static rule earns 0.27 more (p 0.028); both tuned rules keep about 8 points more per-gNB compliance. AXIOM beats every learned baseline (+1.18 single-agent, +1.58 independent, +4.28 MAPPO, 27% more than MAPPO, all p <= 0.005).
- **C1 and C2 fail.** With a per-gNB SLA penalty AXIOM keeps 79.2% per-gNB compliance against 77.3% under the original reward (p 0.65) and does not beat the static rule (79.9%). Every learned baseline falls 13.7 to 18.5 points below AXIOM in every seed under that reward.
- **D1 fails.** VDN ties AXIOM at three gNBs (Env A 12.664 vs 12.698, Holm p 0.15; Env B 8.552 vs 8.832, Holm p 0.056). At 19 gNBs hex AXIOM keeps 13.6 points more compliance (97.0% vs 83.4%) and 2.73 more reward, Holm p <= 0.0003. VDN beats the independent DQN in every cell.
- **E1 holds.** At 110% and 120% load (19 gNBs hex) AXIOM keeps 63.4% and 21.7% priority compliance, 24.3 to 34.0 and 2.5 to 6.4 points above every learned baseline, Holm p <= 0.0052. The static rule keeps 65.5% and 21.9%.
