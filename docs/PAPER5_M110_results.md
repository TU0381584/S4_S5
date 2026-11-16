# M110: per-gNB SLA compliance of the stored Env A policies (results)

These are the results for docs/PAPER5_M110_preregistration.md, committed in d59ee624 (2026-11-16 20:43:14) before any campaign run. The analysis is experiments/results/m110/analysis.json, produced by m110_analysis.py as committed. Nothing was changed after the runs.

## Runs

All 304 jobs exited 0 (experiments/logs/m110/done.txt, 20:43 to 22:39 on 2026-11-16). All 1,620 re-evaluations equal their stored evaluations exactly in reward, blocks and cluster-level SLA flags. None is missing and none is inexact. The duplicate evaluation logs were deleted as pre-registered, and each run keeps its per_gnb_sla.json and row.json (31 MB in total).

## Priority-slice compliance, per gNB and at cluster level (%)

| Policy | 3 gNBs | 7 gNBs | 19 gNBs | 37 gNBs |
|---|---|---|---|---|
| AXIOM | 99.7 / 99.0 | 99.0 / 97.1 | 99.0 / 97.4 | 98.4 / 94.9 |
| DQN-SA | 98.8 / 97.1 | 91.1 / 78.5 | 95.1 / 64.8 | 91.6 / 58.5 |
| DQN-I | 97.9 / 94.0 | 94.9 / 75.8 | 94.6 / 56.5 | 93.9 / 32.7 |
| MAPPO | 85.9 / 79.8 | 82.1 / 68.4 | 87.4 / 61.3 | 85.8 / 56.3 |

Each cell is per gNB / cluster level. Runs per cell are 60 at 3 gNBs, 90 at 7, 180 at 19, and at 37 gNBs 120 for AXIOM and 60 for each baseline.

## AXIOM minus each baseline, per gNB (points, Holm over three baselines at each size)

| Size | DQN-SA | DQN-I | MAPPO |
|---|---|---|---|
| 3 | +0.84, p 0.011 | +1.73, p 6.9e-05 | +13.74, p 5.7e-10 |
| 7 | +7.91, p 5.6e-11 | +4.19, p 2.8e-13 | +16.95, p 7.5e-15 |
| 19 | +3.92, p 4.2e-24 | +4.35, p 1.2e-25 | +11.58, p 1.2e-27 |
| 37 | +7.35, p 1.7e-09 | +5.02, p 1.3e-09 | +13.13, p 1.2e-09 |

## Decision rule

The rule asked for a lead over the closest learned baseline of at least 5 points with Holm p below 0.05 at 19 and at 37 gNBs. At 37 gNBs the lead is 5.02 points over DQN-I and the rule holds. At 19 gNBs the lead is 3.92 points over DQN-SA, which is significant but below 5 points, so the rule does not hold there.

## What this means for the paper

AXIOM leads every learned baseline per gNB at every size, and every lead is significant. The leads are far smaller than at cluster level: 4.2, 3.9 and 5.0 points over the closest baseline at 7, 19 and 37 gNBs, against 18.6, 32.6 and 36.3 points at cluster level. The baselines keep 82 % to 95 % per gNB. Most of the cluster-level gap comes from the metric, which fails a step when any one gNB misses its SLA.

As the pre-registration requires, the paper now says so. The abstract, contribution 2, Section 6.2 and the conclusion name the headline values as cluster-level and state the per-gNB lead of 3.9 to 5.0 points. Online Resource 1 (Section S6) holds the table and the decision rule's outcome. These edits were made under the review's standing rule 6 and are flagged for the author.
