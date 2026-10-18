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

(filled in as development proceeds)
