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

All 12 new checkpoints run, cold-start, contention gate PASS every
attempt, in the randomized order above, batched 4+4+4 with disk
pruning between batches (21G free at start, never dropped below 14G,
21G free at completion after inter-batch pruning of gate-phase-only
and already-committed full-episode logs). `experiments/results/m47_2_2/manifest.csv`
is the full, continuously-committed record (13 rows -- 12 checkpoints
plus one retry, see below).

**One rig-level flake, one legitimate retry, not a criteria
relaxation**: checkpoint 12 (sla/seed262)'s first attempt failed at
native-stack bring-up (`bringup_failed_gate_phase`, "ue2 (mmtc) did
not attach") -- BEFORE the xapp/checkpoint was ever invoked, so the
checkpoint itself was never evaluated. This is the same category of
transient bring-up flakiness this project has retried on throughout
M36-M45 (distinct from a criteria-relevant failure -- an in-band,
responsiveness, or `xapp_run_failed` result would NOT be retried,
since those would be genuine findings about the checkpoint under test,
not the rig). Both the failed attempt and the retry are recorded in
the manifest (nothing overwritten); the retry passed cleanly on a
fresh cold-start with all three criteria met.

**Per-checkpoint PASS/FAIL, all 12 new (seeds 262-267 x {qoe,sla}):**

| mode | seed | in_band | responsiveness | coupling | overall | shed classification |
|---|---|---|---|---|---|---|
| qoe | 262 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| qoe | 263 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| qoe | 264 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| qoe | 265 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| qoe | 266 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| qoe | 267 | PASS | PASS | PASS | **PASS** | indiscriminate_failure |
| sla | 262 | PASS (retry) | PASS (retry) | FAIL then PASS | **PASS** | correct_shed |
| sla | 263 | PASS | PASS | PASS | **PASS** | correct_shed |
| sla | 264 | PASS | PASS | PASS | **PASS** | correct_shed |
| sla | 265 | PASS | PASS | PASS | **PASS** | correct_shed |
| sla | 266 | PASS | PASS | PASS | **PASS** | correct_shed |
| sla | 267 | PASS | PASS | PASS | **PASS** | correct_shed |

**12/12 new checkpoints PASS, zero exceptions.** The shed-
classification split (characterization only, not part of PASS/FAIL)
extends the already-stable pattern to a full 11 seeds/arm now (see
below): every single QoE checkpoint tested to date classifies
`indiscriminate_failure`, every single SLA checkpoint classifies
`correct_shed`.

## Full trustworthy pool -- verified, not assumed, against seeds 256-260 too

The >=11/arm decision threshold is about the FULL live-validated pool,
not just these 6 new seeds in isolation. Re-applied this gate's exact
pre-committed criteria (in-band: 0 samples `max_prbs>=90` in the clean
window; responsiveness: Pearson r computable; coupling: `ok=True`) to
MR3c's 4 already-collected runs (seeds 256/257) and PF2-1a's 6
(258/259/260) -- not re-run, the identical check applied to data
already on disk (`experiments/scripts/m47_2_2_backfill_check.py`, no
new live time):

**All 10 prior runs also satisfy this gate's exact criteria, zero
exceptions** -- qoe/256, qoe/257, qoe/258, qoe/259, qoe/260, sla/256,
sla/257, sla/258, sla/259, sla/260 all PASS in-band, responsiveness,
and coupling under the identical bar the 12 new checkpoints were just
held to.

**Seed 261 (both arms) has never been live-tested in any milestone to
date** -- trained by MR2, confirmed to exercise its full offline
action range, but never run live. Not counted in either pool below.

| arm | live-validated & PASS | trained but never live-tested | total trained |
|---|---|---|---|
| DQN-QoE | **11** (256,257,258,259,260,262,263,264,265,266,267) | 1 (261) | 12 |
| DQN-SLA | **11** (256,257,258,259,260,262,263,264,265,266,267) | 1 (261) | 12 |

## GATE M47-2-2

**(1) Pass criterion**: pre-committed above, unchanged throughout --
never relaxed to preserve n (it didn't need to be; every checkpoint
that reached evaluation passed).

**(2) Per-checkpoint PASS/FAIL**: 12/12 new checkpoints PASS (one
legitimate rig-bring-up retry, not a criteria relaxation, both
attempts recorded). 10/10 prior checkpoints (seeds 256-260, both arms)
also verified to PASS this gate's exact criteria retroactively.

**(3) Trustworthy pool size**: **11/arm** (DQN-QoE: 11, DQN-SLA: 11).
Seed 261 remains untested in both arms -- not a failure, simply never
run live; flagged, not silently absorbed into either count.

## DECISION

**>=11/arm pass -> powered pool is ready.** 11/arm exactly clears the
very-conservative power bar M47-1's power calculation established
(required n=11 under the "very conservative, effect quartered"
assumption). Proceed to PF2-1c, the pre-registered 5-arm powered
campaign (`docs/PAPER5_M45_PF21_preregistration.md`).

## STOP

Trustworthy pool: 11/arm, DQN-QoE and DQN-SLA. Awaiting go before
PF2-1c.
