# M105: does checkpoint selection change the AXIOM-versus-DQN verdicts at scale? (pilot results, 2026-11-12)

Pre-registration: docs/PAPER5_M105_preregistration.md (9530fabe). Analysis: experiments/scripts/m105_analysis.py, committed with it before any run. Output: experiments/results/m105/analysis.json. All 150 jobs exited 0 (04:16 to 10:13). A separate smoke test of the two DQN arms on seed 10099 (Env B, 7 ring, scratch folder, not part of the study) confirmed that the runner applies selection to them.

## Pre-registered outcome: the full rerun is called needed

Both triggers fired.

1. Verdict change. In Env B at 7 gNBs ring, AXIOM against DQN-I is within chance with last checkpoints (reward +2.76, Holm 0.055; compliance +8.1 pp, Holm 0.39). With selected checkpoints AXIOM is ahead (+2.61, Holm 0.039; +12.9 pp, Holm 0.041). The change is in AXIOM's favour. It rests on the smallest Holm p that 10 seeds can give (0.039), so it is fragile.
2. Lead erosion. In Env A at 37 gNBs, AXIOM's reward lead over DQN-SA falls from +55.4 with last checkpoints to +23.6 with selected ones, below half.

No verdict moved against AXIOM. All 16 tests that have AXIOM ahead under last checkpoints keep it ahead under selection: every Env A cell, and Env B at 19 gNBs. Env B at 7 gNBs against DQN-SA is within chance under both.

## Last against selected, AXIOM minus baseline (10 seeds, Holm over 20 in each family)

| Cell | Baseline | Reward, last | Reward, selected | Compliance pp, last | Compliance pp, selected |
|---|---|---|---|---|---|
| Env A 37 hex | DQN-SA | +55.38 (10/0/0) | +23.62 (10/0/0) | +41.47 | +38.64 |
| Env A 37 hex | DQN-I | +24.95 (9/1/0) | +20.31 (10/0/0) | +59.51 | +38.57 |
| Env A 19 hex | DQN-SA | +9.61 (9/1/0) | +11.96 (10/0/0) | +27.43 | +34.27 |
| Env A 19 hex | DQN-I | +12.45 (10/0/0) | +11.94 (10/0/0) | +40.30 | +33.81 |
| Env B 19 hex | DQN-SA | +6.53 (10/0/0) | +6.84 (10/0/0) | +4.92 | +5.05 |
| Env B 19 hex | DQN-I | +8.71 (10/0/0) | +6.97 (10/0/0) | +5.01 | +4.71 |
| Env A 7 hex | DQN-SA | +3.08 (9/1/0) | +2.70 (9/1/0) | +17.42 | +12.91 |
| Env A 7 hex | DQN-I | +5.98 (10/0/0) | +4.70 (10/0/0) | +28.74 | +21.96 |
| Env B 7 ring | DQN-SA | +1.76, within chance | +0.49, within chance | +3.43, within chance | +1.57, within chance |
| Env B 7 ring | DQN-I | +2.76, within chance | +2.61, ahead | +8.13, within chance | +12.88, ahead |

All other entries are "AXIOM ahead" at Holm 0.039. Ten seeds cannot give a smaller Holm p over 20 tests.

## What drives the triggers (descriptive, after the pre-registered analysis)

- The lead erosion is two DQN-SA runs. At 37 gNBs, DQN-SA's last checkpoint on seeds 10004 and 10006 earns -15.4 reward per step, with 12% compliance. Selection replaces both with the accept-all policy (156.6 and 156.4). Without those two seeds, AXIOM's lead is +24.14 under both checkpoint choices. The erosion measures DQN-SA's catastrophic stopping points, not a smaller AXIOM advantage.
- At 37 gNBs selection turns both DQN baselines into the accept-all policy. DQN-SA's selected checkpoint is collapsed in 9 of 10 runs (7 of 10 last) and DQN-I's in 9 of 10 (1 of 10 last). On 8 of 10 seeds the two baselines' selected results are identical to each other. The DQN baselines cannot learn a better policy than accepting everything at this size, and validation picks that policy when training passes through it.
- Selection also raises DQN-I's collapse count at 19 gNBs (Env A, 0 to 6 of 10; Env B, 0 to 3 of 10) while raising its reward (+2.86 and +2.04).
- AXIOM gains least from selection: +2.61 at A37 (2 of 10 runs change), +2.35 at A19, +0.30 at B19, +0.03 at A7 and +0.55 at B7. At A37 selection removes AXIOM's one collapsed run (10006, 156.4 to 177.9) and repairs a partial one (10004, 70% to 100% compliance), as in M104.

## What a full rerun would change, and what it would not

- It would not change any claim's direction: AXIOM stays ahead of both DQN baselines in every Env A cell and in Env B at 19 gNBs.
- It would change numbers: AXIOM's reward lead over DQN-SA at 37 gNBs (catastrophic DQN-SA last checkpoints are removed), AXIOM's compliance lead over DQN-I at 37 (59.5 to 38.6 pp), and the collapse panel, where the DQN baselines' collapse rates would rise and AXIOM's would fall to near zero.
- It would probably add an AXIOM-ahead verdict against DQN-I in Env B at 7 gNBs. That needs the full seed count to confirm.
- Three gNBs (M67) is the one size where selection removes AXIOM's significant lead over DQN-SA (+0.350 to +0.046).

## Options for the author

1. Keep the paper's procedure (last checkpoint) and report M67 and M105 as a robustness check: selection leaves every verdict at 7, 19 and 37 gNBs in place or in AXIOM's favour, shrinks AXIOM's lead at 3 gNBs to a tie with DQN-SA, and turns the DQN baselines at 37 gNBs into the accept-all policy. This is honest without a rerun, because the pre-registered rule's triggers are disclosed with their causes.
2. Adopt selection for every value-based arm and rerun everything (about 700 runs, 1.5 to 2 days). The figures and tables would change as described above. The 3-gNB claim against DQN-SA would become a tie.

The pre-registered rule says the rerun is needed, and this document does not overrule it. The choice is the author's. The manuscript is unchanged.

## Audit notes (2026-11-12)

An independent recomputation (experiments/scripts/audit_m102_m106.py) reproduces every test above from the raw logs, with its own reader and statistics. Four table entries were first rounded from 3-decimal values (for example 21.965 shown as +21.97). They now show the stored values rounded once (+21.96, +0.49, +1.57, +12.88). A sign-flip permutation test agrees with the Wilcoxon verdicts on 39 of 40 tests. The exception is AXIOM against DQN-I on reward in Env B at 7 gNBs with last checkpoints, Holm 0.055 by Wilcoxon and 0.047 by permutation. That is the reward half of trigger 1, so the verdict change there depends on the choice of test. M106 found AXIOM ahead on reward in that cell with either checkpoint.
