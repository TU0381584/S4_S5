# M106: the two cells where checkpoint selection changes a claim (results, 2026-11-12)

Pre-registration: docs/PAPER5_M106_preregistration.md (1aeb6fd0). Analysis: experiments/scripts/m106_analysis.py, committed with it before any run. Output: experiments/results/m106/analysis.json. All 150 jobs exited 0 (10:20 to 12:56).

## Answers

- Q1, no. With selected checkpoints, AXIOM is not ahead of DQN-SA on reward in Env A at 3 gNBs: +0.037 per step, CI [+0.003, +0.082], p 0.036, Holm 0.106, W/T/L 15/9/6, within chance. On the same runs with last checkpoints AXIOM is ahead: +0.510, Holm 0.0046, 21/4/5. That replicates the paper's current claim on fresh seeds. M67's development result therefore holds on 30 fresh seeds: selection reduces AXIOM's three-gNB reward lead over DQN-SA to a margin this sample cannot separate from zero. On compliance AXIOM stays narrowly ahead under selection: +0.38 pp, Holm 0.047, 8/22/0.
- Q2, yes. With selected checkpoints, AXIOM is ahead of DQN-I in Env B at 7 gNBs ring on reward (+2.24, Holm 1.5e-5, 20/0/0) and on compliance (+7.57 pp, Holm 0.042, 15/0/5). M105's verdict change replicates. On these fresh seeds AXIOM is ahead on reward with last checkpoints as well (+1.78, Holm 0.0013, 18/0/2), so the change is on compliance (+1.24 pp, 10/0/10 with last checkpoints, against +7.57 with selected ones). M105's reward change partly reflected its 10-seed sample.

## All tests (fresh seeds, Holm over 8 in each family)

| Cell | Baseline | Measure | Selected: diff, Holm, W/T/L | Last: diff, Holm, W/T/L |
|---|---|---|---|---|
| Env A 3 | DQN-SA | reward | +0.037, 0.106, 15/9/6, within chance | +0.510, 0.0046, 21/4/5, ahead |
| Env A 3 | DQN-SA | compliance | +0.382, 0.047, 8/22/0, ahead | +3.806, 0.028, 11/17/2, ahead |
| Env A 3 | DQN-I | reward | +0.887, 1.8e-5, 29/1/0, ahead | +1.242, 2.1e-5, 29/1/0, ahead |
| Env A 3 | DQN-I | compliance | +4.468, 3.1e-4, 22/7/1, ahead | +6.949, 2.8e-4, 22/8/0, ahead |
| Env B 7 ring | DQN-SA | reward | +0.007, 0.996, 10/0/10, within chance | +0.049, 1, 8/0/12, within chance |
| Env B 7 ring | DQN-SA | compliance | -3.961, 0.996, 11/0/9, within chance | -6.768, 0.316, 7/0/13, within chance |
| Env B 7 ring | DQN-I | reward | +2.244, 1.5e-5, 20/0/0, ahead | +1.783, 0.0013, 18/0/2, ahead |
| Env B 7 ring | DQN-I | compliance | +7.573, 0.042, 15/0/5, ahead | +1.239, 1, 10/0/10, within chance |

## Descriptive only (not confirmatory)

- Pooled with M67's 20 development seeds (selected checkpoints, 50 seeds), AXIOM minus DQN-SA at 3 gNBs is +0.041 reward, CI [+0.010, +0.076], p 0.013, 24/15/11. Those seeds shaped Q1, so this does not confirm anything. It suggests a real but very small lead.
- Pooled with M105's 10 seeds in Env B at 7 gNBs (30 seeds), AXIOM minus DQN-I under selection is +2.37 reward (29/0/1) and +9.34 pp compliance (23/0/7). Against DQN-SA it is +0.17 and -2.1 pp, both within chance.
- Selected minus last reward: DQN-SA gains most at 3 gNBs (+0.506, 17/10/3), then DQN-I (+0.388) and AXIOM (+0.033, 7/23/0). In Env B at 7 gNBs: DQN-SA +1.04, AXIOM +1.00, DQN-I +0.54. No run collapsed in either cell under either checkpoint choice.

## Reading, with M67 and M105

Checkpoint selection mostly helps the baselines, because AXIOM's last checkpoint is already its best or close to it in most runs. Across sizes:

- 3 gNBs: AXIOM's reward lead over DQN-SA falls from clear to within chance (M67, M106). This is the one claim selection weakens.
- 7 gNBs, Env B: AXIOM's lead over DQN-I gains significance on compliance (M105, M106). AXIOM and DQN-SA remain tied.
- 7, 19 and 37 gNBs, Env A, and 19 gNBs, Env B: every AXIOM-ahead verdict holds (M105). At 37 gNBs selection turns both DQN baselines into the accept-all policy.

## Proposed wording, if the author keeps the last-checkpoint procedure (option 1 in M105)

A robustness paragraph or OR1 section could say: "Selecting each value-based learner's checkpoint on held-out validation episodes, applied equally to AXIOM and both DQN baselines, leaves every comparison at 7, 19 and 37 gNBs in place and adds AXIOM's compliance lead over DQN-I in Env B at seven gNBs. At three gNBs it lifts the single-agent DQN to within 0.04 reward per step of AXIOM, a difference that is not significant on 30 fresh seeds after Holm correction over the eight tests (raw p 0.036)."

The paper's three-gNB claim against DQN-SA would then need a qualifier in the main text, whichever option is chosen. The manuscript is unchanged.

## Audit notes (2026-11-12)

An independent recomputation (experiments/scripts/audit_m102_m106.py) reproduces every test from the raw logs except one p-value. For AXIOM against DQN-SA on compliance at 3 gNBs with last checkpoints, two seeds' differences are mathematically equal but are stored about 1e-14 apart. The pre-registered analysis therefore ranks them as distinct and reports p 0.0079 (Holm 0.032). With the tie recognised, p is 0.0071 (Holm 0.028). The verdict is the same, and no other p-value in M98 to M106 changes when ties are recognised. Since 2026-11-12 the shared test recognises ties, so analysis.json and the table above report the tie-corrected value.
