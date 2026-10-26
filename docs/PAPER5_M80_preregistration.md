# M80: equal-budget baselines, unreproduced cells, and fresh seeds at nineteen gNBs (pre-registration)

Committed on 2026-10-27, before any M80 run. The user asked for further reruns of low-confidence or weaker results, to check that every reported result is accurate. Every check is reported whether it holds or fails, and nothing here replaces a reported result. Runners: m64_run.py, m73_run.py and m75_run.py, unmodified; the framework is not modified. Output goes to experiments/results/m80/. Analysis: experiments/scripts/m80_analysis.py, using the independent reader in m66_verify.py. Parts run in the order A, C, D, B; any part not finished when the compute window closes is reported as not run, never estimated.

## A. Equal training budget in Env B at seven gNBs (ring, seeds 900-911 and 1000-1002)

M79 H3 trains AXIOM for 900 episodes. A gives the three learned baselines the same 900 episodes: DQN-SA (initialisation seeded, as in M73/M75), DQN-I and MAPPO, through m75_run.py. DQN-SA is also rerun at 300 episodes with its seeded initialisation, because the stored M64 DQN-SA is unseeded.

- A1. At 900 episodes AXIOM keeps more priority-slice compliance than each baseline at 900 episodes, Holm over 3, adjusted p < 0.05.
- A2. At 900 episodes AXIOM earns more reward per gNB than each baseline at 900 episodes, Holm over 3, adjusted p < 0.05.
- Reported: each baseline at 900 against itself at 300 episodes, mMTC-only seed counts, and AXIOM at 900 episodes against the stored tuned local rule.

## C. Exact reproduction of cells no earlier campaign reran (seed 900)

Each run is compared with the stored log for the same seed. A cell reproduces if reward, block count and every per-slice SLA agree within 1e-9.

- Env A, seven gNBs, ring (m65_scaling/n7_ring, m64_run.py --env A): AXIOM, DQN-I, MAPPO.
- Env A, nineteen gNBs, hex (m65_scaling/n19_hex): AXIOM, DQN-I, MAPPO.
- Env A, thirty-seven gNBs, hex (m73/A_n37_hex, m73_run.py): AXIOM, DQN-SA, DQN-I, MAPPO.
- Env B, seven gNBs, hex and fully connected (m64/n7_*, m64_run.py): AXIOM, DQN-I, MAPPO.
- C holds if every listed run reproduces. DQN-SA in m64/m65 is not listed because its stored initialisation was unseeded (M66 V1). Any run that does not reproduce is reported with the size of the difference and its cause, if one is found.

## D. Fresh seeds in Env B at nineteen gNBs (hex, seeds 7000-7014, never used before)

Same runner and settings as M75 D (m75_run.py, M75_PERGNB=1, 300 episodes): AXIOM, DQN-SA (seeded), DQN-I, MAPPO, the static rule, accept-all, and the local rule carried over from seven gNBs.

- D1. AXIOM earns more reward per step than each learned baseline, Holm over 3, adjusted p < 0.05.
- D2. AXIOM keeps more per-gNB priority-slice compliance than each learned baseline, Holm over 3, adjusted p < 0.05.
- D3. The static rule earns more reward per step than AXIOM on average (the paper reports this unfavourable result).
- D4. The carried-over local rule earns more than AXIOM in at least 13 of 15 seeds.
- Reported: collapses per arm, mMTC-only AXIOM seeds, cluster compliance.

## B. Training budget in Env B at nineteen gNBs (hex, seeds 900-907)

AXIOM trained for 900 episodes through m75_run.py with M75_PERGNB=1, compared on the same seeds with the stored 300-episode M75 D AXIOM and the stored static rule. Diagnostic only; baselines are not rerun at 900 episodes here.

- B1. Fewer seeds are mMTC-only than in the stored run on the same seeds.
- Reported: reward and per-gNB compliance against the stored AXIOM and the static rule, paired.
