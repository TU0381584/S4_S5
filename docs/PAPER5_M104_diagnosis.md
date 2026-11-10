# Exploratory diagnosis of AXIOM's collapsed runs at 37 gNBs (2026-11-11)

Not pre-registered and not a reported result: it reads stored training logs and re-evaluates stored checkpoints, and it motivates M104. Scripts: the scratch files collapse_diag.py and collapse_probe.py, whose logic is reproduced below.

1. Training trajectories. For every AXIOM run at 37 gNBs (M73 hex 30 seeds, M96 8000 to 8019, M101 9960 to 9979; 70 runs, 8 collapsed at evaluation) and every MLP run (M100, M101; 40 runs, none collapsed), the per-episode training rollups give blocked requests by slice. Mean mMTC blocks per episode in the last 50 training episodes: AXIOM healthy 682, AXIOM collapsed 508, MLP 655. Five of the eight collapsed runs (8002, 8010, 9964, 919, 924) blocked 755 to 780 mMTC requests per episode at the end of training, as many as healthy runs. The other three blocked 23 to 123.

2. Final training episode, step by step (episode 300). Runs 8002, 8010 and 919 switch within the episode between steps that block nearly every mMTC request and steps that accept them all. 8002 ends in an accepting phase over its last six steps; 8010 and 919 switch to accepting partway through and stay there. Healthy run 8000 blocks mMTC at every step to the end.

3. Re-evaluating the stored checkpoints greedily, 5 episodes each, no learning:
   - On the evaluation stream (5000 + seed): 8002 and 8010 block 0 requests; 8000 blocks 4,338 mMTC requests.
   - With exploration at the training rate (epsilon 0.05), still no learning: 8002 and 8010 block only the random share (about 100 per slice); 8000 blocks 4,214 mMTC.
   - On the training stream (seed): 8002 and 8010 block 0; 8000 blocks 4,307 mMTC.

Reading: the collapsed runs learned to shed mMTC but their greedy mMTC decision was unstable at the end of training, and the checkpoint was taken at the last step, in an accepting phase. This is the failure M67 described at three gNBs ("the failure is in which weights training happens to stop on").
