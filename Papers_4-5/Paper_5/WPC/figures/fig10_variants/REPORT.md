# Fig. 10 variants, report

Four redesigns of Fig. 10 (A to D, plus D_alt), each rendered from stored results by a standalone script in this folder. The manuscript .tex and the existing Fig. 10 source were not edited for this work. Side-by-side previews are in contact_sheet.pdf, and the source of every value is in DATA_MANIFEST.md.

## Measured width

`\textwidth` of the WPC template (sn-jnl.cls with the paper's options `pdflatex,sn-basic,Numbered`), from a pdflatex probe: 372.0 pt = 130.7 mm. Every variant is exactly 130.7 mm wide. The current paper figures are 119 mm wide, the Springer artwork maximum the submission has used so far. A variant chosen for the manuscript would need either a redraw at 119 mm or a decision to use the full text width.

## Phase 0 findings

### Gate

No stop condition was met.
- Every value on the current Fig. 10 traces to a result file, except the typed labels listed below, which are tagged in DATA_MANIFEST.md.
- Per-seed data exists for compliance (eval logs, 15 to 60 evaluations per controller), delay (M77 recorder, 30 seeds per controller), the load-shift comparisons, the federated cost and the MAPPO margin.
- Finding (a) shows no error.

### Sources

The full table is in DATA_MANIFEST.md. In brief:
- **Parameter counts:** m64/complexity.json and m73/complexity_n37.json.
- **Transfer compliance:** M92 (m92/A_*_n37/*_transfer).
- **SLA compliance at 37 gNBs:** m73/A_n37_*.
- **URLLC delay:** M77 kpi.urllc.delay_steps. This is mean backlog divided by mean served PRBs per control period, so its unit is control periods.
- **Past tuning load:** M96 b, and M76 for the static rule.
- **+8.7:** m76/b1_shift_n19 at 120% load.
- **27–36% over MAPPO:** m64/n3_fully_connected and m75/D_envB_n19_hex.
- **Private training:** 30 paired seeds from m65_reviewer, m65_m3, m66_fresh and m66b_fresh.
- **7–44× delay and 35.0 points:** derived from the delay and compliance rows.

CIs are 95% percentile bootstraps from scipy (10,000 resamples). They can differ from the paper's in the last digit, e.g. AXIOM's 93.7% has [89.9, 97.0] here against [89.8, 97.2] in the paper.

### (a) Why 93.7% at 37 gNBs but 95–96% after transfer

The two numbers come from different checkpoints and seeds, and there is no error.
- **93.7%** is AXIOM trained at 37 gNBs, pooled over 60 evaluations: hex 30 seeds, ring 15 and fully connected 15. Some of these seeds collapse, 6 of 60 per the paper's table.
- **95–96%** (95.4 hex, 96.3 ring, 96.3 fully connected) is the AXIOM checkpoint trained at 7 gNBs (m65_scaling/n7_*), run unchanged at 37 gNBs (M92) on 15 seeds per layout. None of these collapses.
- **Same seeds compared:** on M92's own seeds, AXIOM trained at 37 keeps 94.8, 93.2 and 94.4%. The transferred-minus-trained differences are +0.6, +3.2 and +1.9 points at p = 0.92, 0.87 and 1.0. On the fresh M96a seeds the difference is +4.1 at p = 0.37.
- **Conclusion:** transfer is not significantly better. The two figures are simply different measurements, and the paper reports both correctly.

### (b) What "Tuned rule: 7 to 19" means

It refers to Env B. The local threshold rule tuned at 7 gNBs on the hex layout (m64/n7_hex/rule_local_selection.json) was run unchanged at 19 gNBs (m75/D_envB_n19_hex/rule_local_transfer, and the M76 load shifts). There it still leads AXIOM at nominal load by 3.33 reward per step.

### (c) Why the tuned rule was "not tested" at 37 gNBs

The tuned rule families were only ever defined and run for Env B, and every 37-gNB result is Env A. Following your previous request, this is now measured.
- **Run:** M97 was pre-registered (docs/PAPER5_M97_preregistration.md, commit 33522657) before any run. It tunes the local family on Env A training streams at 37 gNBs (hex, the baselines' 30 seeds) with the unchanged runner.
- **Selected rule:** the run selected τ_c = 0 with no queue thresholds. That is exactly the static rule, which sheds every mMTC request. Four grid entries tie for the top training score, all with τ_c = 0, and the runner keeps the first.
- **Result:** held-out compliance 99.98% and URLLC delay 0.030 control periods, identical to the static rule on all 30 seeds. All 30 recorder re-runs reproduced their stored logs. The analysis is in experiments/results/m97/analysis.json.
- **Remaining n/t:** only the tuned rule's Env A transfer cell (7 to 37 gNBs), since that rule was never carried across sizes in Env A.

### A finding the current figure hides

Past the tuning load in Env B at 19 gNBs (M76), the static rule beats the carried tuned rule by more than AXIOM does:

| Reward per step over the tuned rule | 110% | 115% | 120% |
|---|---|---|---|
| Static rule | +8.05 | +9.46 | +10.63 |
| AXIOM | +6.23 | +7.55 | +8.67 |

Under steady load the static rule trails the tuned rule by 2.5 and AXIOM by 3.8.
- **Current figure:** it marks the static rule's past-load cell "ties". That comes from a different comparison, AXIOM against the static rule in Env A.
- **Effect on the text's claim:** if the static rule's cell used this Env B comparison, the static rule would also meet seven of eight criteria under the design-based private-training entries. "AXIOM alone meets seven of its eight criteria" would then no longer hold.
- **Paper text:** it already says the static rule does better at 19 gNBs under coupling. Options A and C use the Env B comparison for every controller, so they show this. Which definition to use is your call.

### Private training

Only AXIOM was trained federated. Its cost is +0.49 reward per step, CI [−0.07, 1.10], p = 0.14, over 30 seeds.

For the other controllers, A and C give entries that follow from the training design the paper states:
- MAPPO's critic reads every gNB's features.
- DQN-SA learns over the joint state.
- DQN-I trains each gNB on its own requests.
- The rules learn no model.

These entries are tagged BY DESIGN in the manifest. They are not measurements.

## Variants

All sizes are exact canvas sizes with no tight-bbox cropping. The smallest font is the smallest of all visible text artists, measured at that final size.

The palette measured in CAM02-UCS:

| Mode | AXIOM vs learned | AXIOM vs rules | Learned vs rules |
|---|---|---|---|
| Colour | 28.1 | 62.4 | 35.1 |
| Greyscale (L* only) | 7.5 | 8.5 | 1.0 |
| Deuteranopia | 28.1 | 56.2 | 29.1 |

So the deuteranopia simulation keeps all three apart, while greyscale separates learned controllers from rules only by marker fill, line style and position.

### A: dot-plot strips and capability table

| Item | Result |
|---|---|
| Size | 130.7 × 104.0 mm |
| Smallest font | 8.0 pt |
| Greyscale | Yes. Families are split by a divider, learned markers are filled and rule markers hollow, and every row is named. |
| CVD | Yes. All palette distances stay at 28 or more. |
| HARDCODED | No plotted number. The labels "fixed input", "size-free" and "7→19, Env B" (traceable, see manifest) and the five design-based private-training entries. |

Dropped relative to the current Fig. 10:
- the "Learns its rules" row and the criteria-met score;
- the 7–44× delay and 27–36% over-MAPPO margins as stated numbers (the delays are plotted);
- "+8.7", replaced by each controller's mean over 110 to 120% (AXIOM +7.5), so that every cell uses the same statistic.

### B: trade-off scatter

| Item | Result |
|---|---|
| Size | 130.7 × 84.0 mm |
| Smallest font | 8.0 pt |
| Greyscale | Yes, marginal. Controllers differ by marker shape, fill and label, and the two rule lines by style. In panel b, AXIOM's ellipse differs from the grey ones only by an L* difference of 7. |
| CVD | Yes. |
| HARDCODED | None, apart from the "fixed input" cross. |

Dropped:
- past-load, steady-load and private-training comparisons;
- "Learns its rules" and the score;
- all six margin numbers as text.

Notes:
- AXIOM's transfer arrow is almost invisible, because its 7-gNB compliance (97.1%, three layouts pooled) and its compliance after transfer (96.0%) nearly coincide. That is the result, not a drawing fault.
- In panel b, DQN-SA's mean delay of 3.6 sits outside its ellipse. Two collapsed seeds with delays of 34 and 62 pull the arithmetic mean far from the geometric centre, and the caption says so.

### C: annotated normalised heatmap (cividis)

| Item | Result |
|---|---|
| Size | 130.7 × 92.0 mm |
| Smallest font | 8.0 pt |
| Greyscale | Yes. Cividis is monotonic in lightness, and every cell prints its value. |
| CVD | Yes. Cividis is designed for this. |
| HARDCODED | The private-training row keeps words: measured for AXIOM, design for the others (flagged in CHANGELOG.md as asked). Rules' parameter growth is shown as "no params" at the target. |

Dropped:
- "Learns its rules" and the criteria-met row, as asked;
- the margin numbers are not stated, though every raw value is printed.

Weakness: per-row normalisation lets one outlier set a row's scale. For example, DQN-I's 57.9-point shortfall makes the rules' 99.98% compliance look nearly neutral.

### D: radar chart (comparison only), with D_alt

| Item | Result |
|---|---|
| Size | 130.7 × 84.0 mm each |
| Smallest font | 8.0 pt |
| Greyscale | Marginal. MAPPO and the static rule are both thin solid lines, and DQN-SA and the tuned rule both dashed. They differ only by vertex markers. |
| CVD | Yes. |
| HARDCODED | None. Missing values break the outline: rules have no parameters, DQN-SA and DQN-I cannot transfer, and the tuned rule's Env A transfer is n/t. |

Dropped:
- every raw value and margin;
- private training and "Learns its rules".

Order sensitivity: compare fig10_D_alt.png. Moving the parameter axis between two axes where AXIOM scores high changes the visual area considerably.

## State of the repository

- **Committed:** only docs/PAPER5_M97_preregistration.md (33522657).
- **Uncommitted, new:** experiments/scripts/m97_analysis.py, experiments/results/m97/, experiments/logs/m97/ and this folder.
- **Uncommitted, edited before this brief:** experiments/plots/paper5_fig_capability.py and experiments/scripts/m66_verify.py were changed in the previous request (decisive private-training cells, M97 cells for the tuned rule). They have not been touched since, and Fig. 10 has not been regenerated from them.
- **Nothing pushed.**
