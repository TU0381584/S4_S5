# M47-2-2 — live trust-gate the 12 new checkpoints (LIVE, batched, resumable)

Per Stage 12's own established finding (offline convergence predicts
nothing about live behavior for this architecture family), none of
M47-2-1's 12 new checkpoints (seeds 262-267 x {qoe,sla}) enters the
powered PF2-1c pool without passing this gate first.

## Pre-committed pass/fail criterion (fixed BEFORE any run, not relaxed to preserve n)

A checkpoint PASSES iff ALL THREE hold, computed on the precise clean
window MR3c validated (`t >= first M46DBG e2_apply write`, per slice):

1. **In-band rate ~100%** = **zero samples with `max_prbs >= 90`** for
   BOTH urllc and embb in the clean window. This is MR3c's own
   validated "0.0% uncapped after write" standard (`docs/PAPER5_M46_MR3c_clean_revalidation.md`)
   -- the exact threshold that distinguishes a real control-path
   regression (the catastrophic ~106/boot-default excursion MR3b/c
   fixed) from ordinary graded accept/reject variation. **Not** the
   stricter "observed values are a literal subset of {floor..cap}"
   test -- MR3c's own already-trustworthy checkpoints (256/257, both
   arms) showed occasional 1-2-unit near-misses past floor/cap in 4 of
   8 (run,slice) pairs and are not disqualified by that stricter
   standard; requiring it here would relax nothing for genuine control
   failures while manufacturing false FAILs on ordinary graded
   behavior.
2. **State-responsiveness present** = the per-slice Pearson r (own
   commanded ceiling vs own backlog, same method as PF2-1a) is
   COMPUTABLE (not `None` -- i.e. at least 3 samples with nonzero
   variance in both series) for BOTH urllc and embb in the clean
   window. The SIGN is reported and compared against PF2-1a's OBSERVED
   pattern (both slices negative, protect-by-reject) as
   CHARACTERIZATION, per this gate's own explicit instruction -- NOT
   itself a pass/fail threshold, since PF2-1a's own trustworthy
   checkpoints already showed real sign/magnitude variation (-0.98 to
   +0.27) without that variation disqualifying any of them.
3. **Coupling-tolerant** = the contention gate PASSES, the live xapp
   subprocess completes with `ok=True` (no timeout, no crash, no
   aborted teardown), for the full E4 co-located episode
   (urllc 3600Kbps/12x, embb 12000Kbps/3x, mmtc native).

PWC/PWC_eq/shed-classification are logged per checkpoint as
characterization only, per this gate's own instruction -- they do not
affect PASS/FAIL here (that judgment is PF2-1c's, at power).

## Run order -- randomized, fixed in advance

`random.seed(47220); random.shuffle(pairs)` over all 12 (mode, seed)
pairs (documented, reproducible, not re-rolled after seeing any
result) -- avoids biasing the trustworthy pool toward whichever arm/
seed happens to run first, given this rig's own documented cumulative-
session-length instability (Stage 15, M38-era):

1. qoe/264, 2. qoe/262, 3. qoe/266, 4. qoe/265, 5. sla/265, 6. sla/267,
7. sla/266, 8. sla/264, 9. sla/263, 10. qoe/263, 11. qoe/267, 12. sla/262

Batched 3-4 per session; `experiments/results/m47_2_2/manifest.csv`
committed after EVERY checkpoint clears (not batched), so a mid-block
hang loses at most the one in-flight run, never prior results.

Per-checkpoint results land under `experiments/results/m47_2_2/{mode}/seed{N}/`.
Live episode logs (M41DBG/M46DBG instrumented gNB logs, same binary
MR3b/MR3c/PF2-1a already validated -- no rebuild needed) under
`experiments/logs/`.

## Results

(Filled in incrementally as each checkpoint clears -- see
`experiments/results/m47_2_2/manifest.csv` for the authoritative,
continuously-committed record; this section is the narrative summary,
updated at the end of each batch, not the source of truth during the
run.)
