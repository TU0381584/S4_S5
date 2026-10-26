# M79: why AXIOM trails DQN-SA in Env B at seven gNBs (pre-registration)

Committed on 2026-10-27, before any M79 run. The user asked why AXIOM lags in Fig. 6b at Env B, seven gNBs. This campaign is diagnostic. AXIOM's definition (m64_axiom2.py) is not changed, no reported number is replaced, and every check is reported whether it holds or fails. Runners: experiments/scripts/m64_run.py and m76_run.py, unmodified; the framework is not modified. Output goes to experiments/results/m79/. Cell: Env B, seven gNBs, ring, seeds 900-911 and 1000-1002 (S15), the Fig. 12b cell.

## Observed before this commit, from the stored M64 logs

- AXIOM at seven gNBs earns about DQN-SA's reward per gNB (3.36 against 3.37, pooled over the three layouts) but keeps less priority-slice compliance (35.1% against 44.3%).
- In 28 of 45 AXIOM seeds (fully connected 9, ring 11, hex 8) every evaluation block is an mMTC block, which is the static rule's behaviour. AXIOM's reward and compliance there match the static rule (3.37, 33.6%). At three gNBs 0 of 30 AXIOM seeds do this. DQN-SA and DQN-I do it in 0 of 45 seeds at seven gNBs. The MLP-encoder variant does it in 13 of 45.
- The best rule at both sizes sheds every mMTC request and sheds eMBB when the gNB's URLLC queue reaches 0.2 (3.91 per gNB, 60.5%). AXIOM at seven gNBs misses the eMBB part.
- In training, AXIOM's mMTC share of blocks rises to 0.85-0.93 by episode 300 at seven gNBs, against about 0.7 at three gNBs and 0.6-0.75 for DQN-SA at seven.
- The reward charges each slice's SLA penalty once for the cluster when any gNB violates. AXIOM's per-gNB Q-heads see one gNB's neighbourhood but regress on that cluster reward, so one gNB's eMBB shedding pays only when the other gNBs also comply. At M76 C (nineteen gNBs) a per-gNB penalty cut AXIOM's mMTC-only seeds from 13 to 4 of 15 without a significant compliance gain.
- At M64's three-gNB pilot, LR 3e-4 raised AXIOM's mMTC share of blocks to 0.94 and LR 3e-3 lowered it to 0.66.

## R. Reproduction

- AXIOM seeds 900, 901, 902 rerun with m64_run.py. R holds if each evaluation reward equals the stored M64 value within 1e-9.

## H1. Credit assignment (per-gNB SLA penalty, M76_REWARD=pergnb)

- AXIOM and DQN-SA (seeded, as in M75/M76) train and evaluate under the per-gNB penalty.
- H1a. AXIOM is mMTC-only in at most 5 of 15 seeds (stored: 11 of 15).
- H1b. AXIOM's cluster priority-slice compliance exceeds the stored AXIOM's on the same seeds, paired Wilcoxon.
- Reported: AXIOM against DQN-SA under the per-gNB penalty, compliance and reward per gNB, paired.

## H2. Step size (arm axiom2_lr3e-3)

- H2a. mMTC-only in at most 5 of 15 seeds.
- H2b. Compliance exceeds the stored AXIOM's, paired Wilcoxon.

## H3. Training budget (axiom2, 900 training episodes, three times the original)

- H3a. mMTC-only in at most 5 of 15 seeds.
- H3b. Compliance exceeds the stored AXIOM's, paired Wilcoxon.

H1b, H2b and H3b form one Holm family; each holds at adjusted p < 0.05. Reported for every arm: reward per gNB, priority-slice compliance, mMTC share of blocks, mMTC-only seed count, and the stored DQN-SA and rule values for reference. A variant that helps is not adopted into AXIOM by this campaign; adopting one would need its own pre-registered campaign across every cell.
