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

## Results (campaign 12:35 to 19:42 on 2026-10-21; analysis in experiments/results/m72/analysis.json)

3 of 4 judged criteria hold; 14 rows were reported only.

- **B primary holds.** Under load 1.10, 1.15 and 1.20, AXIOM beats the nominally tuned rule by +0.46, +0.43 and +0.35. It wins 23, 23 and 21 of 25 seeds, at Holm p ≤ 0.0002.
  - Nominal reproduces the stored results exactly.
  - Reported:
    - Load 0.80: −0.28, p 0.44.
    - Load 1.05: +0.30, p 0.017.
    - Coupling 0.30: −0.31, p 0.28.
    - Amplitude 0.50: +0.18, p 0.045.
    - N=7 ring: −3.84 at nominal, +1.86 at load 1.10, +3.14 at load 1.20.
    - Rule re-tuned on the shifted streams: AXIOM −0.16 (p 0.14) at 1.10, −0.12 (p 0.14) at 1.15, −0.62 (p 2e-5) at 1.20.
- **A is split.**
  - Headroom holds: the hindsight-best rule earns 0.14% more than the tuned rule on 15 seeds.
  - The eMBB bound fails narrowly: the per-seed best-eMBB rule averages 37.7%, above the stated 37%. The manuscript sentence now quotes 37.7%.
- **C verdict: "equivalent".** No Holm-significant difference over the 8 tests. VDN is ahead in Env A N=3, Env B N=3 and Env A N=19 ring, and behind in Env B N=7 ring. AXIOM is not replaced.
- **D (reported).** 900-episode AXIOM gains +0.33 (p 0.008) in Env B N=3 and +2.92 (p 0.0005) in Env B N=7 ring. Its gaps to the tuned rule fall to 0.08 (p 0.35) and 0.96 (p 0.064).
- **Stream note.** The C training streams (9000-9019) coincide with the evaluation streams of M66d seeds 4000-4019. No model is evaluated on a stream it trained on.
