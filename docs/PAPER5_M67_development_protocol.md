# M67: development protocol for a more reliable AXIOM

Committed on 2026-10-19, before any M67 run.

## Why

On every Env A three-gNB sample, AXIOM ties the oracle more often than the single-agent DQN (27 against 13 of 40 seeds in M66d). A few of its runs still end on a poor final policy (5 of 40), which cancels most of that advantage. Those runs have training curves indistinguishable from good runs, so the failure is in which weights training happens to stop on.

The goal is to make AXIOM's training reliable enough that it beats both DQN baselines decisively in Env A at three gNBs. That is the one cell where it does not do so today.

## Rules

1. **Development seeds.** Development uses seeds 7000-7019 only. Their evaluation streams are 12000-12019. No development run touches seeds 900-1009, 3000-3019, 4000-4039, or the confirmatory seeds 8000-8039.
2. **Validation streams.** Every in-training choice, such as which checkpoint to keep, is made on validation streams 20000 + seed. These are disjoint from every training and evaluation stream.
3. **Equal treatment.**
   - A change to the training procedure is applied to every value-based learned arm, meaning AXIOM, the independent DQN, and the single-agent DQN. Examples are checkpoint selection, learning-rate schedules, and target-network updates.
   - The single-agent DQN uses the seeded initialisation wrapper.
   - Only a change to AXIOM's architecture may be applied to AXIOM alone.
4. **Budget.** At most 8 AXIOM variants are tried in development. Every variant, its development result, and the reason it was kept or dropped is logged in this file's results section, including failures.
5. **Development cells.**
   - Primary: Env A, N=3, seeds 7000-7019.
   - Secondary: Env A at 1.02 load, seeds 7000-7019.
   - Guard cells, to catch a variant that helps here but hurts elsewhere: Env B N=3 and Env A N=7 ring, seeds 7000-7009.
6. **Development target.**
   - On the primary cell, AXIOM beats the seeded single-agent DQN and the independent DQN, each trained with the same procedure, at p < 0.01, with at most 2 losses in 20.
   - On the secondary cell, AXIOM beats both at p < 0.05.
   - On the guard cells, AXIOM's reward is not significantly below current AXIOM v2.
7. **Freeze and confirm.**
   - The first variant to meet the target, or the best one when the budget runs out, is frozen. Its code is committed together with a confirmatory pre-registration.
   - One confirmatory run follows, on new seeds 8000-8039 (Env A N=3) and 8000-8019 (load 1.02), for every arm under the frozen procedure.
   - "Decisive" means AXIOM beats the single-agent and independent DQNs at Holm-adjusted p < 0.01 at N=3, and at p < 0.05 at load 1.02.
   - The confirmatory result is reported whether or not it is decisive.
8. **Stopping.** If no variant meets the development target within the budget, development stops and that is reported. A likely reason would be that the baselines also reach the oracle once their own checkpoints are selected, leaving no room to win.
9. **Manuscript.** If a frozen variant is adopted, every AXIOM and baseline campaign in the paper must be rerun under the new procedure before any number changes. The paper must also disclose this development stage and the number of variants tried.

## Variant log

**V1: validation-based checkpoint selection, all value-based arms.** Run 02:08 to 04:46 on 2026-10-19; analysis in experiments/results/m67_dev/V1/analysis.json. Target not met.

- Primary cell, Env A N=3:
  - AXIOM reaches 12.816 against the oracle's 12.815, so it is at the ceiling.
  - Selection lifts the single-agent DQN almost as much, so AXIOM's lead falls from +0.350 with last checkpoints (p 0.036) to +0.046 (p 0.084, W/T/L 9/6/5).
  - Against the independent DQN AXIOM leads by +0.646 (p 1e-4, 19/1/0).
- Secondary cell, load 1.02: AXIOM leads the single-agent DQN by +0.067 (p 0.068) and the independent DQN by +0.211 (p 0.048).
- Guard cells are unharmed: +0.277 in Env B N=3 and +0.072 in Env A N=7 ring, against last-checkpoint AXIOM v2 on the same runs.

Decision: development in the Env A three-gNB cell stops under rule 8. AXIOM already matches the oracle there, and the single-agent DQN comes within 0.05 of it once its own checkpoints are selected. No legitimate AXIOM change can open a decisive gap. Variants used: 1 of 8.

## Amendment 1 (committed 2026-10-19, after V1 and before any confirmatory run)

Env B at seven gNBs has real headroom: the tuned local rule earns about 27.4 and the learners 22 to 25. The manuscript currently says AXIOM does no better than the DQN baselines there.

Existing results show that AXIOM v2 with the per-node MLP encoder, already an arm in the paper (axiom2_mlp), beats both DQN baselines there more consistently than the graph-attention encoder.
- On fresh seeds it beats the single-agent DQN at p ≤ 0.037 and the independent DQN at p ≤ 0.02 in all three layouts.
- On the main sample it beats the independent DQN at p ≤ 0.007 in every layout, but not the single-agent DQN (p 0.12 to 0.45).

This observation was made on reported samples, so it is a hypothesis, not a result. It is tested once on new seeds below. No V1 checkpoint selection is used, so every arm is trained exactly as in the manuscript, and the single-agent DQN uses the seeded wrapper.

| Cell | Seeds | Arms | Decisive if |
|---|---|---|---|
| Env B, N=7, fully-connected, ring, hex | 8100-8109 | AXIOM v2 MLP, AXIOM v2 (GAT), seeded single-agent DQN, independent DQN | AXIOM v2 MLP beats the single-agent DQN and the independent DQN on reward under every layout, all 6 comparisons at Holm-adjusted p < 0.05. The same 6 comparisons for AXIOM v2 with GAT are reported, not predicted. |

The result is reported whether or not it is decisive. If it is decisive, adopting the MLP encoder as AXIOM's encoder would be a design change. Every campaign that uses AXIOM would then need the MLP encoder before the manuscript changes. The paper would also have to disclose that the change was chosen after seeing these samples, and that only this confirmation is independent of that choice.


### Amendment 1 result: not decisive

Run 04:49 to 07:31 on 2026-10-19; analysis in experiments/results/m67_confirm_envB/analysis.json.

- **AXIOM v2 MLP vs independent DQN:** holds in every layout. +1.97 / +2.97 / +2.79 for fully-connected / ring / hex, 9 or 10 of 10 seeds, Holm p ≤ 0.016.
- **AXIOM v2 MLP vs seeded single-agent DQN:** fails in every layout. +1.39 / +0.92 / +1.29, 7 or 8 of 10 seeds, Holm p 0.32 / 0.32 / 0.32.
- **AXIOM v2 with GAT, reported only:**
  - vs independent DQN: +1.93 / +2.49 / +2.01, Holm p 0.078 / 0.068 / 0.035.
  - vs single-agent DQN: +1.35 / +0.43 / +0.51, Holm p ≥ 0.32, with 5/5 splits on ring and hex.
- **MLP minus GAT:** +0.04 / +0.48 / +0.78, none significant.

Conclusion: the MLP encoder is not adopted. In Env B at seven gNBs, neither AXIOM encoder beats the single-agent DQN decisively on ten new seeds. Both lead it on average, by 0.4 to 1.4 per step.

Development stops here. A larger sample in the hope of crossing the threshold would be optional stopping after a near miss. The only legitimate route is a new pre-registered study, run alongside this one and reported with it.
