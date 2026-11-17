# Which headline numbers changed in the pre-submission review, and why

Every row comes from an entry of CHANGELOG_WPC.md (Gate and number in the last column). The verifier recomputes each value from the stored logs.

| Claim in the paper | Before | Now | Why | Entry |
|---|---|---|---|---|
| Abstract, 37 gNBs | lead over the best learned baseline "with a URLLC backlog delay 7 to 44 times shorter" | the backlog clause is removed, and the lead stays 36.3 to 36.5 points with 7,782 parameters against 5,122 for MAPPO and up to 682,058 for DQN-I | the quantity is a normalised backlog from a fluid model, not a measured delay | 2.01, 2.35, 2.42 |
| Role of graph attention | "adds little", at most 0.068 reward per step | "no consistent benefit": the per-node MLP encoder trails AXIOM slightly in Env A at three gNBs and leads it by 1.38 reward per step in Env B at seven gNBs on fresh seeds | the evidence points both ways | 2.04, 2.37, 2.41 |
| Env A, three gNBs, AXIOM over DQN-SA | 0.311, p 0.066 on the first 30 seeds | 0.312, 95 % CI [0.10, 0.55], Holm p 0.0021 on the pooled 60 seeds | the pre-registered seed extension (M107) doubled the sample | 2.33 |
| Env B, three gNBs, tuned neighbour rule over AXIOM | within chance on the first 30 seeds | ahead by 0.235 reward per step, p 0.012, while AXIOM keeps 1.2 points more priority-slice compliance, p 0.012 | the same extension | 2.38 |
| Env A, 7-gNB ring, AXIOM over DQN-SA | significant on the original seeds | not reproduced on the added seeds alone (smallest lead 7.2 points, p 0.11), confirmed on 30 further seeds: +1.94 reward per step and +11.8 points of compliance, p below 0.001 | original, added, pooled and confirmation samples are reported separately | 2.39, Gate 3 |
| Env B, three gNBs, AXIOM compliance lead over the neighbour rule | pooled only | confirmation seeds leave it within chance | same | 2.39 |
| Differential privacy | "weak formal guarantee" | "no meaningful privacy guarantee", epsilon about 2,600 or more | wording matched to the number | 2.40 |
| Live testbed | "never jointly validated in a live deployment" | "we found none jointly validated", and the main paper states AXIOM was not deployed live | absolute claims limited to what was checked | 2.07, 5.03 |
| Scaling lead in Env A | compliance above 93 % against below 84 % for every learned baseline, stated without naming the metric | the same values named as cluster-level, with the per-gNB lead over the closest baseline stated: 4.2, 3.9 and 4.99 points at 7, 19 and 37 gNBs (cluster level 16.9, 31.8, 36.3) | M110 re-evaluated all stored runs per gNB (2,130 with M111); the pre-registered 5-point rule is missed at both 19 and 37 gNBs | 7.03 to 7.06, 9.04 |
| Env A, three gNBs (second extension, M111) | AXIOM ahead of DQN-SA in reward (0.312, p 0.0021) and compliance, ahead of the MLP encoder in reward, static rule ahead within chance | pooled on 75 seeds: ahead of DQN-SA in reward only (0.230, p 0.0097), compliance lead 1.3 points within chance, MLP encoder within chance, static rule ahead (0.138, p 0.007), AXIOM at 98.9 % of the static rule's reward | 15 more seeds per Env A cell, pooled; the 15 newest alone do not reproduce the leads over DQN-SA and the MLP encoder | 9.01, 9.02 |
| Abstract | AXIOM earns 42 % more than the static rule in Env B at 3 gNBs | clause removed | room for the per-gNB sentence within 250 words | 7.04 |
| Verification | 674 checks | 769 checks, all pass | checks added for every new table and sentence | Gates 2, 3, 5 and after |

## Added by the review

- Learning curves (new Fig. 5) and a table of effect sizes with Hodges-Lehmann estimates and rank-biserial correlations (Table 4), both recomputed from stored logs.
- A fourth sample, 30 confirmation seeds, reported on its own and pooled into no estimate.
- A paragraph on what the model omits relative to standard slice-admission formulations.

## Reported in Online Resource 1 since the gates

M109 (240 jobs, fresh seeds 13000 to 13009) is in Section S6 with every arm. It changes none of the numbers above. Parity baselines with Huber loss and LayerNorm and a parameter-shared MLP baseline stay 29 to 71 points below AXIOM at 19 and 37 gNBs at cluster level, and QMIX matches AXIOM at 19 gNBs but fails the pre-registered stability rule in all 10 seeds.
