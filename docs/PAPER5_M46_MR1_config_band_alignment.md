# M46-MR1 — a training config whose action ranges land inside the live-measured bands

NO RIG. Static config construction + offline audit, first step of the
retrain-revalidate cycle scoped at the end of M45-PF2-0
(`docs/PAPER5_M45_PF2_train_eval_consistency.md`). Fixes PF2-0's fatal
action-space-exclusion confound (urllc's submission config could never
produce a live ceiling above 4 raw PRB, entirely excluding its own
confirmed 6-8 PRB band) in isolation, before touching the separate
cross-slice-coupling confound (`ClosedLoopKpmSource` has no cross-slice
term at all) -- that is later work, explicitly out of scope here.

## What was built

`experiments/configs/m46/saclb_m46_train.yaml` (new). Derived, not
multiplied: each controllable slice's `min_ratio_floor`/`max_ratio_cap`
is set so `raw_prbs = (106 * ratio_pct) // 100` (the same conversion
M41/M42 already established and cited from `gNB_scheduler_dlsch.c`) lands
exactly on the bottom/top of that slice's own already-measured graded
band, not a blind rescale of the old broken config (the existing
`saclb_campaign_m41fix_test.yaml` is explicitly verification-only and was
not reused as a training config, per this milestone's standing
constraint).

| slice | floor ratio% -> raw | nominal ratio% -> raw | cap ratio% -> raw | target band | source |
|---|---|---|---|---|---|
| urllc | 6 -> 6 | 7 -> 7 | 8 -> 8 | 6-8 raw PRB | M44-D, commit `d3a9d12` |
| embb | 5 -> 5 | 7 -> 7 | 10 -> 10 | 5-10 raw PRB | M44-E2b, commit `4fb98dc` |
| mmtc | 5 -> 5 | 5 -> 5 | 5 -> 5 | N/A (fixed by design) | M44-E1/E1b, commits `1e8d2b8`/`074b6ec` |

`nominal_ratio=7` for both controllable slices is a documented **design
choice** (a low/mid starting point inside each band), not a measured
quantity -- it does not enter the floor/cap verification below.

mmtc is deliberately **not** given a graded range. M44-E1/E1b already
established it has no realistic controllable band at any load this
project has found (its only graded band appears at ~320x true native
rate, categorically non-mMTC traffic). Rather than imply mmtc is part of
this campaign's controllable action space, its ratio is collapsed to a
single fixed point (`floor == nominal == cap == 5`), parked exactly at
the scheduler's minimum grant size -- the specific value M44-E1 already
confirmed mmtc serves cleanly at, at its own native/realistic load. mmtc
stays present and served in the environment; it is just explicitly not
an actionable dimension of this policy's output, by documented choice.

Everything not related to the ratio/action-space fix (reward weights,
QoE mapper checkpoints/coefficients, arrivals, episode length, NSSAI
identifiers) is carried over unchanged from
`saclb_campaign_v2_offline_train.yaml` -- out of scope for MR1.

## Static verification

`experiments/scripts/m46_config_band_alignment.py` (new) -- reuses
`m42_floor_matrix.py`'s own `raw_prbs()`/`parse_slices()` helpers (same
constants: `N_RB_SCHED_INIT=106`, `MIN_RBSIZE=5`, same conversion already
cited and verified against source in M41/M42) rather than re-deriving the
arithmetic independently, so this check is against the SAME floor matrix
methodology the milestone asked for, not a parallel one that could
silently disagree. For each slice, enumerates every integer ratio point
in `[floor, cap]` and computes the actual DISTINCT raw-PRB values that
range expresses (not assumed linear from the endpoints -- this would
have caught the same kind of off-by-one rounding skip M42 documented
elsewhere in this project's ratio-to-PRB conversions, e.g. ratio=17
mapping to raw=18, not 17, at higher ratio values than used here).

Full output: `experiments/results/m46_mr1/config_band_alignment.csv`.
Also independently confirmed the file loads cleanly through the real,
frozen `qoe_oran_framework.config.load_saclb_config()` (the actual
loader MR2's training code will use, not just this audit's own regex
parser) and reports identical floor/nominal/cap values.

| slice | floor raw | nominal raw | cap raw | target band | in_band | distinct points expressible |
|---|---|---|---|---|---|---|
| urllc | 6 | 7 | 8 | 6-8 | **True** | 3 -- {6, 7, 8}, exactly M44-D's tested points |
| embb | 5 | 7 | 10 | 5-10 | **True** | 6 -- {5,6,7,8,9,10}, exactly M44-E2b's tested points |
| mmtc | 5 | 5 | 5 | N/A (fixed by design) | N/A | 1 -- fixed at min_rbSize, matches M44-E1's confirmed-healthy floor point |

## GATE MR1 verdict

**Both urllc and embb: in-band AND multi-point-graded.** Every ratio
value either controllable slice's policy could ever select maps to a
raw-PRB value inside that slice's own already-measured, real graded
band -- no value in either range falls below the scheduler's 5-PRB
floor, and no value falls outside the tested band's upper edge either.
The range width is not collapsed: urllc's 3-unit range expresses all 3
of M44-D's tested points exactly; embb's 6-unit range expresses all 6 of
M44-E2b's tested points exactly. mmtc's fixed single point sits exactly
at the scheduler minimum, the specific value M44-E1 confirmed healthy at
native load -- not starved, not pretending to be controllable.

**Per this milestone's own decision tree: the config confound is
resolved statically.** Proceeding to MR2 (offline retrain under this
fixed, independent-per-slice-controllable env) is unblocked on this
specific axis. This does NOT resolve PF2-0's second confound (the
training KPM source's lack of cross-slice coupling, unrelated to ratio
ranges) -- that remains open for a later step, as this milestone's own
scope explicitly separated the two.

## STOP

Per the milestone's instruction, reporting the alignment table and
verdict here. Awaiting go before MR2.
