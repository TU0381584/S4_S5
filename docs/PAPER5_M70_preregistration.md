# M70: referee-response runs (pre-registration)

Committed on 2026-10-20, before any M70 run. These runs answer the third internal review (M1-M3 of that review). Every check is reported whether it holds or fails, and nothing here replaces a result already reported. Runner: experiments/scripts/m70_run.py (a wrapper; the framework and m64_run.py are untouched). Output goes to experiments/results/m70/.

## R1. Reference rule at seven and nineteen gNBs (Env A)

The scaling figure shows only learned policies. The static rule that sheds every mMTC request is run on the same seeds as the scaling campaign, so it can be shown alongside AXIOM.

- Cells: N=7 under the fully-connected, ring and hex layouts, seeds 900-911 and 1000-1002; N=19 under the same three layouts, seeds 900-926 and 1000-1002.
- Expected: priority-slice compliance of at least 99% in every cell. Reported as measured.

## R2. Single-agent DQN with its initialisation seeded

The reported single-agent DQN has the unseeded-first-seed issue disclosed in the paper. It is rerun through experiments/scripts/m66c_seeded_single.py in every scaling cell not yet rerun.

- Cells: Env A N=7 under all three layouts and N=19 under the fully-connected and hex layouts (N=19 ring was rerun in M66c), on the scaling seeds; Env B N=7 under all three layouts, seeds 900-911 and 1000-1002.
- Prediction: in Env A, AXIOM beats the seeded single-agent DQN on priority-slice compliance and on reward under every layout at both sizes, at Holm-adjusted p < 0.05 within each size (6 tests per size). Env B N=7 is reported, not predicted.

## R3. MAPPO tuning grid and training budget

Only two MAPPO configurations were tried before: the defaults, which collapsed, and the tuned set. A full grid now runs on the pilot seeds.

- Grid: actor learning rate {3e-4, 1e-3, 3e-3} x epochs {4, 10} x minibatch {64, 256} x training episodes {300, 900}, 24 configurations. All other settings are unchanged.
- Pilot seeds: 2000-2004, in Env A N=3 and in Env B N=3.
- Selection: per environment, the configuration with the highest mean pilot reward. Ties go to the smaller budget.
- Confirmation on the main seeds, with each environment's selected configuration: Env A N=3 (seeds 900-929), Env A N=19 ring (scaling seeds), Env B N=3 (seeds 900-929), Env B N=7 ring (seeds 900-911 and 1000-1002). If a 900-episode configuration is selected, MAPPO trains three times longer than every other arm, and this is disclosed.
- Prediction: AXIOM beats the selected MAPPO on reward in Env A N=3, Env A N=19 ring and Env B N=3, and also on priority-slice compliance at N=19, at Holm-adjusted p < 0.05 over these four tests. Env B N=7 ring is reported, not predicted.

## R4. Ablations of AXIOM's design choices

The paper attributes AXIOM's behaviour to two choices that were never ablated in a controlled test.

- A1, per-slice heads: AXIOM v2 with its three per-slice Q-heads replaced by one shared, parameter-matched head (2,127 against 2,118 parameters) that takes the slice one-hot as an input.
- A2, per-request TD samples: AXIOM v2 trained on one joint value-decomposition target per step (the summed chosen Q-values regressed on the reward plus the summed next-step maxima) instead of one TD sample per pending request.
- Cells: Env A N=3 (seeds 900-929), Env B N=3 (seeds 900-929), Env A N=19 ring (seeds 900-911 and 1000-1002). Each variant is compared with the stored AXIOM v2 results on the same seeds, which reproduce exactly (M66 V1).
- Tests: paired Wilcoxon on reward and on priority-slice compliance, Holm over the 6 tests per variant.
- A design choice counts as supported if AXIOM is significantly better than the variant in at least one cell and significantly worse in none. Otherwise the manuscript's design rationale is reworded to match the result.
