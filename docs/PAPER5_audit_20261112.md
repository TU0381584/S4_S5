# Verification of M98 to M106 and of the manuscript's statistics (2026-11-12)

Requested by the author: check, review and verify all findings, especially the recent runs, for authenticity, accuracy and error-free analysis and presentation.

## What was checked and how

1. Independent recomputation of M102 to M106 (experiments/scripts/audit_m102_m106.py, output experiments/results/audit_m102_m106.json). It has its own log reader and its own Holm, bootstrap and sign-flip permutation test, and imports no campaign analysis code. Every test in the M103, M104, M105 and M106 analysis files (70 tests) and every M102 pilot score was recomputed from the raw evaluation logs and compared field by field: n, wins, ties, losses, mean, median, p, Holm p, bootstrap CI and verdict.
2. Provenance, all 564 jobs of M102 to M106:
   - every job exited 0;
   - each job log names the arm, environment, size, layout, seed, encoder variant and environment flags of its launch line, and contains no traceback;
   - every evaluation has 50 episodes;
   - every selection record (380) has the right snapshot set, picks the best validation score with ties to the later, and matches the evaluation logs;
   - spot-checked validation logs have 10 episodes and the stored score.
3. Encoder identity: the eight M102 encoders' checkpoints have exactly the execution parameter counts in the M103 results table (7,782, 8,279, 9,814, 3,430, 3,190, 3,638, 3,494 and 5,030).
4. Fresh seeds: no M102 to M106 seed appears in any other result folder, and none of their evaluation (5000 + seed) or validation (20000 + seed) streams was ever a training seed.
5. Pre-registration order: each pre-registration and analysis script was committed before its campaign launched, and none was changed afterwards. In M102 and M106 the commit and the launch fall in the same second because one shell command ran both, commit first.
6. Document numbers: every test of M98 to M106 was matched against its results document. The M98 to M101 analyses reproduce byte for byte from the compressed logs (done on 2026-11-12, commit 2f3dafeb).
7. Collapse diagnosis (docs/PAPER5_M104_diagnosis.md):
   - Items 1 to 3 had been computed with scratch scripts that were never committed and are now lost. They were rebuilt as experiments/scripts/m104_collapse_diag.py. Every number reproduces: 682, 508 and 655 mMTC blocks per episode; 755 to 780 and 23 to 123 for the collapsed runs; the step patterns of 8002, 8010, 919 and 8000; and 0, 0 and 4,338 blocks greedy, about 100 per slice with exploration, and 0, 0 and 4,307 on the training stream.
   - Items 4 and 5 and the M104 addition reproduce exactly from experiments/scripts/m104_instability_diag.py.
8. Tie handling in the Wilcoxon test, across M98 to M106 and across the manuscript verifier (see below).

## Results

Everything reproduces, apart from the presentation errors and one statistical subtlety below. No result was invented, no run is missing, and no verdict in M98 to M106 changes.

### Errors found and corrected in the results documents (commit d8284423)

- M105 table: four entries were rounded from 3-decimal values instead of the stored values (21.965 shown as +21.97). They are now +21.96, +0.49, +1.57 and +12.88.
- M104 results: the MLP's Env B advantage was attributed to "M67, M99 and M103". M67 found no significant MLP-minus-GAT difference (+0.04, +0.48, +0.78). It now cites M98 and M99, and M103 on hex against the concat variant.
- M104 diagnosis item 2 said the accepting steps "accept them all". The training log shows 0 to 4 of about 42 pending requests blocked per step, at 5% exploration. It now says "nearly all".
- M106 proposed wording said the three-gNB difference is "not significant on 30 fresh seeds". The raw p is 0.036, so it now says not significant after Holm correction over the eight tests.
- Diagnosis provenance: the document now points to the rebuilt, committed script.

### Statistical subtlety: floating-point ties in the Wilcoxon test

Differences that are mathematically equal, or mathematically zero, are sometimes stored about 1e-14 apart. scipy then sees no ties and uses its exact no-tie distribution, or counts a zero as a win or loss. Recognising ties, by rounding differences to 1e-9, gives the tie-corrected test.

- M98 to M106: 1 of 142 p-values changes. It is M106, AXIOM against DQN-SA on compliance at 3 gNBs with last checkpoints, p 0.0079 to 0.0071 and Holm 0.032 to 0.028, with the verdict unchanged. It is recorded in the M106 results.
- Manuscript verifier: 23 p-values change and none crosses 0.05. 660 of the 663 checks still pass. The three that would change are two printed values:
  - main.tex, Env B at seven gNBs, ring layout: "AXIOM keeps less compliance than DQN-SA, at Holm-adjusted p=0.011" becomes 0.012 with ties recognised. The verdict is unchanged.
  - Online Resource 1, Table S10, row "3 gNBs, 300 episodes": the tree-against-AXIOM Holm p 0.0012 becomes 0.0016. The verdict is unchanged.
- One win-tie-loss count in the verifier is affected by a zero stored as 5.6e-17: Env B, seven gNBs, fully connected, AXIOM against DQN-SA on compliance. It is 6/0/9 as stored and 5/1/9 with the tie, p 0.073 against 0.056, not significant either way. The paper does not print this count.
- The other 20 changes are p-values printed as below 0.001, or not printed. The largest relative change, an exact 1.9e-9 against a tie-corrected 1.7e-6, is printed as below 0.001 in both cases.

### Robustness notes

- The sign-flip permutation test agrees with Wilcoxon on 69 of 70 M103 to M106 verdicts. The exception is M105, AXIOM against DQN-I on reward in Env B at 7 gNBs with last checkpoints: Holm 0.055 by Wilcoxon and 0.047 by permutation. It is recorded in the M105 results. M106 resolved the cell, with AXIOM ahead on reward under either checkpoint choice.

## Proposed manuscript corrections (awaiting the author; main.tex and the OR1 are unchanged)

1. Either keep 0.011 and 0.0012, which are the pre-registered pipeline's values, or switch to the tie-corrected values, 0.012 and 0.0016. Switching means applying tie-aware rounding in m66_verify.paired everywhere, which changes only these two printed numbers, and updating two verifier checks. Keeping them is defensible because the pipeline is pre-registered. Switching is the more exact statistic.
2. The M98 to M106 wording proposals in the results documents stand as corrected above.
