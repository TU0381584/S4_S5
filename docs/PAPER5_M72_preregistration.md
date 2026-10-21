# M72: confirmatory follow-ups to the third review's Tier 3 probes (pre-registration)

Committed on 2026-10-21, before any M72 run. The M71 probes (commit c106ec1) were exploratory, so every M72 test uses seeds the probes did not touch. Every check is reported whether it holds or fails. Output goes to experiments/results/m72/.

## C. The joint-target (VDN) variant on fresh seeds

The M70 ablation found that training AXIOM on one joint value-decomposition target per step (m70_run.py, M70_VARIANT=vdn) is never significantly different from AXIOM v2 and trends better. That was found after the reported campaigns, so it is tested once on new seeds.

- Arms: AXIOM v2 and the VDN variant, both trained from scratch.
- Cells and seeds:
  - Env A N=3, seeds 9000-9019.
  - Env B N=3, seeds 9000-9019.
  - Env A N=19 ring, seeds 9000-9009.
  - Env B N=7 ring, seeds 9000-9009.
- Tests: paired Wilcoxon on reward and on priority-slice compliance, Holm over all 8 tests.
- Verdict: "improved variant" if the VDN variant is significantly better in at least one test and worse in none; "equivalent" if no test is significant; "worse" otherwise. AXIOM in the manuscript is not replaced by this test, whatever its outcome.

## B. AXIOM against rules tuned on nominal conditions, under shifted conditions

The probe suggested that AXIOM degrades more gracefully than the tuned rule when load rises beyond what the rule was tuned for. Stored AXIOM v2 checkpoints and the rule tuned on nominal training streams are evaluated without retraining or retuning (m72_shift.py).

- Primary cell: Env B N=3, checkpoints 905-929 (25 seeds; 900-904 were used by the probe).
- Shifts:
  - load base 0.80, 1.05, 1.10, 1.15 and 1.20 times the nominal shares;
  - coupling 0.30;
  - load amplitude 0.50;
  - nominal, which must reproduce the stored results exactly.
- Primary prediction: under load 1.10, 1.15 and 1.20, AXIOM's mean reward exceeds the nominally tuned rule's, paired Wilcoxon, Holm over these 3 tests, p < 0.05.
- Reported, not predicted:
  - the other shifts;
  - priority-slice compliance;
  - Env B N=7 ring (checkpoints 900-911 and 1000-1002) under nominal, load 1.10 and load 1.20;
  - a rule re-tuned on shifted training streams (seeds 905-914) under the three primary shifts, as a reference for what re-tuning recovers.

## A. Env B ceiling: the rule family chosen in hindsight

- Cell: Env B N=3, seeds 900-914.
- Method: every rule of the local family (95 rules) is evaluated on each seed's evaluation stream, and the best is taken per seed in hindsight (m71_probe.py hindsight).
- Predictions: the hindsight-best mean reward is within 1% of the tuned rule's, and no rule keeps mean eMBB compliance above 37%.

## D. Longer AXIOM training in Env B (reported only)

The paper names longer training as a route towards the tuned rule.

- Runs: AXIOM v2 trained for 900 episodes instead of 300 in Env B N=3 (seeds 900-919) and Env B N=7 ring (seeds 900-911).
- Comparisons: the stored 300-episode AXIOM and the tuned rule on the same seeds. Reported without prediction.
