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
| Verification | 674 checks | 735 checks, all pass | checks added for every new table and sentence | Gates 2, 3, 5 |

## Added by the review

- Learning curves (new Fig. 5) and a table of effect sizes with Hodges-Lehmann estimates and rank-biserial correlations (Table 4), both recomputed from stored logs.
- A fourth sample, 30 confirmation seeds, reported on its own and pooled into no estimate.
- A paragraph on what the model omits relative to standard slice-admission formulations.

## Run but not yet in the paper

M109 (240 jobs, fresh seeds 13000 to 13009, results in docs/PAPER5_M109_results.md) leaves every number above unchanged. Parity baselines with Huber loss and LayerNorm and a parameter-shared MLP baseline stay 29 to 71 points below AXIOM at 19 and 37 gNBs, and QMIX matches AXIOM at 19 gNBs but fails the pre-registered stability rule in all 10 seeds. How to report these awaits the authors.
