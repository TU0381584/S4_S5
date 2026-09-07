# M45-PF2-0 — train/eval consistency check for the DQN-QoE vs DQN-SLA pilot

NO RIG. Read-only forensics over already-committed configs, checkpoints,
and prior investigations (M41, M42-G1, M43-P1/P1B-1, Stage 12, M27) --
reusing already-computed, already-verified numbers wherever they exist
rather than recomputing them, per the standing "never invent a number"
rule.

## Which checkpoints and config the pilot would use

Confirmed directly from `experiments/scripts/run_stage15_n128_campaign.sh`
(the actual submission-record N128 campaign orchestrator, `CFG_OF`/`CKPT_OF`
mapping, lines 38-47) -- this is the same checkpoint pair named in the
standing constraints ("submission record... DQN-QoE checkpoint stays
pinned"):

| Arm | Checkpoint | Config | Reward mode |
|---|---|---|---|
| DQN-QoE | `experiments/results/offline_v2/qoe/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt` | `saclb_campaign_v2.yaml` | qoe |
| DQN-SLA | `experiments/results/offline_v2/sla/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt` | `saclb_campaign_v2.yaml` | sla |

Both arms are matched on config, seed, and every hyperparameter except
`--reward-mode` -- confirmed identical invocation shape in the campaign
script. **Arm-vs-arm, this is a clean, apples-to-apples pair.** The
question this gate asks is whether that pair, run in the E4 co-located
regime, isolates reward design -- or whether both arms share a mismatch
against that regime severe enough to make the comparison meaningless.

## (i) Below-floor or above-floor training/eval ceiling ranges?

**Below-floor, confirmed two independent ways, and it is the SAME
below-floor config M41 found and fixed -- just never fixed here.**

`experiments/results/m42_floor_audit/config_floor_matrix.csv` (M42-G1,
already computed, reused not recomputed) gives `saclb_campaign_v2.yaml`'s
per-slice raw-PRB range via the cited conversion
(`raw_prbs = (106 * ratio_pct) // 100`, `min_rbSize=5`):

| slice | floor_raw_prbs | cap_raw_prbs | verdict |
|---|---|---|---|
| urllc | 1 | **4** | **BROKEN** -- cap_raw_prbs < 5, the ENTIRE configured range can never clear the scheduler's hard 5-PRB floor |
| mmtc | 1 | **3** | **BROKEN** -- same |
| embb | 1 | 12 | MARGINAL -- starts below floor at reset, but the cap clears it |

`experiments/configs/saclb_campaign_v2_offline_train.yaml` (the actual
training-time config, confirmed below by `train_offline_live_scale.py`'s
own default) has byte-identical `nominal_ratio`/`min_ratio_floor`/
`max_ratio_cap` values to the live-eval `saclb_campaign_v2.yaml` for all
three slices -- same BROKEN/BROKEN/MARGINAL verdict applies to training,
not just live eval.

Live confirmation, not just static audit: M43-P1B-1's offline replay
across all 28 actual submitted seeds found urllc and mmtc **floor-pinned
(raw PRBs < 5) for 100% of steps, in every single seed, zero exceptions
-- "a deterministic consequence of both slices' cap alone never reaching
5 raw PRBs... regardless of where in their range the policy sits."**

**This directly determines whether the pilot's intended regime is even
reachable.** urllc's own confirmed real graded band (M44-D: 6-8 raw PRB)
and the E4 co-located regime's urllc ceilings (6, 7, 8) all require a
raw-PRB ceiling **above** this config's hard cap of 4. **No action the
DQN-QoE or DQN-SLA policy can output under `saclb_campaign_v2.yaml` can
ever produce a urllc ceiling above 4 raw PRBs** -- the action space
itself excludes the entire E4 urllc range. This is not a soft
behavioral risk; it is a structural impossibility given the config both
checkpoints are matched on. embb's cap (12) does structurally cover
E4's tested embb range (5-10), so embb alone would be reachable, but
urllc -- the slice this pilot most cares about, since PWC is
weight-dominated by it (M45-PF1.4: raising urllc's ceiling 6→7 moved
PWC 5x more than raising embb's ceiling 5→10) -- cannot be.

## (ii) Does the training congestion regime match live?

**No, on two independent, already-established grounds -- one general
(magnitude), one specific to this exact checkpoint family (shape/
correlation).**

**Magnitude (M27):** the offline environment family used across this
project's MARL work was found to have `congestion_level` "capped near
0.03-0.09 by construction... while live measurement on this rig shows
real congestion at 0.23-0.26 (3 UEs) and 0.60-0.69 (6 UEs)" -- a
different offline-env lineage than DQN-QoE/SLA's (`ClosedLoopKpmSource`
vs. the N-UE cluster env M27 characterizes), cited here as prior
evidence that this project's offline environments have repeatedly
under-modeled live congestion magnitude, not as a direct measurement of
this specific checkpoint pair.

**Shape/correlation (Stage 12, directly applicable -- same
`ClosedLoopKpmSource`/`saclb_campaign_v2*` lineage):** 600 held-out
offline episodes across 6 checkpoints of this same training
architecture found **offline held-out compliance has NO relationship to
live compliance** (the 3 checkpoints with a PERFECT live record were
among the WORST offline, and vice versa) and, at the per-step level for
one checkpoint, offline SLA margins were **negative** (routinely
violating) while the identical checkpoint's live margins were strongly
**positive** (comfortably compliant) -- "the same weights produce a
different effective policy against the two KPM sources, because the
states the synthetic random walk puts the policy into are not the
states real traffic puts it into." Stage 12's own conclusion: "no
amount of additional offline simulation, by itself, can be used to
pre-select or validate a 'good' checkpoint before spending live-rig
time" until the KPM source's *dynamics*, not just its mean, are
validated against real traffic -- which has not since been done for
this checkpoint family.

## (iii) Single-slice or multi-slice contended, resembling E4's coupling?

**Multi-slice, but NOT resembling E4's coupling -- confirmed directly
from the training KPM source's own code, not inferred.**

`train_offline_live_scale.py` trains against all three slices
simultaneously (`ClosedLoopKpmSource(..., slice_ids=list(cfg.slice_by_id))`),
so this is not a single-slice training regime. But
`ClosedLoopKpmSource`'s own docstring states its model is computed
**"per (gNB, slice)"**: each slice's served throughput is
`min(offered + backlog, ceiling_prb)` using *that slice's own* last
commanded ceiling -- there is no term anywhere in this class that
reduces one slice's capacity as a function of another slice's ceiling
or load. Structurally, this is N independent per-slice random walks
sharing a training loop, not a shared-PRB-budget contention model.

This is the opposite of E4's confirmed live finding: co-locating urllc
and embb produces a real, reproducible, asymmetric coupling (embb
served% down 6.6-13.1 points at every tested ceiling purely from
urllc's presence), attributed to the real scheduler's cross-slice
`min_prbs` subtraction. **The training environment cannot have taught
either policy anything about this coupling, because the coupling does
not exist in that environment by construction.**

## GATE PF2-0 verdict

**CONFOUNDED, decisively -- not a soft risk.** Two independent,
compounding problems, both already established by this project's own
prior work rather than newly hypothesized here:

1. **Action-space exclusion (fatal for urllc specifically).**
   `saclb_campaign_v2.yaml` structurally caps urllc's live ceiling at 4
   raw PRB -- below the scheduler's 5-PRB floor and below every point in
   its own confirmed real graded band (6-8) and the entire E4 co-located
   regime (6, 7, 8). Running either checkpoint under this config cannot
   produce a live urllc ceiling inside the intended regime **no matter
   what the policy decides**. A pilot run as literally specified (these
   checkpoints + this config, live) would just reproduce M43-P1B-1's
   already-known outcome -- urllc floor-pinned at ~4 raw PRB the entire
   time, only embb's ceiling actually varying with the policy -- which
   is not a test of the E4 co-located regime at all, and PWC's own
   design (weight-dominated by urllc, per PF1.4) would mostly be
   scoring a fixed, unreachable urllc state rather than anything the
   reward mode caused.
2. **Environment mismatch (independent of #1, affects embb too).**
   Both checkpoints were trained and offline-evaluated against
   `ClosedLoopKpmSource`, already shown (Stage 12, same architecture
   family) to produce live-uncorrelated, systematically-harsher,
   differently-shaped per-step dynamics than real traffic, and (by the
   class's own docstring) to contain no cross-slice contention coupling
   at all -- while E4's live regime is defined specifically by a real,
   asymmetric cross-slice coupling. Even for embb, whose action space
   does structurally reach the E4 range, there is no basis to expect
   either checkpoint's *learned behavior* in that range to reflect
   anything the reward mode taught it about this specific contended
   regime, since the regime's defining feature was invisible during
   training.

**Any live effect-size/variance number PF2-1 would measure under the
current checkpoints + config would be confounded by these two
mechanisms, not isolated to reward design (QoE vs SLA).** Per the
milestone's own instruction, PF2-1 does not proceed on this basis.

## What retraining would be needed to isolate reward design

Not a quick fix -- flagged as a real scope decision, not resolved here:

1. **A live-measured, above-floor config for urllc/mmtc.** M44-D has
   now directly measured urllc's real graded band (6-8 raw PRB @
   3600 Kbps); a corrected training config should target ratios
   spanning that band (e.g. `min_ratio_floor`/`max_ratio_cap` chosen so
   the raw-PRB range brackets 6-8), analogous to M41's fix but
   calibrated against M44's own live measurements rather than a blind
   6x multiply (the existing `saclb_campaign_m41fix_test.yaml` is
   explicitly marked verification-only for exactly this reason -- its
   own header says a real fix "should use fresh live PRB measurements,
   not this quick multiply"). embb's existing cap (12) already covers
   its confirmed band (5-10) and would not need to change on this
   count alone.
2. **A training environment whose contention dynamics resemble live.**
   At minimum, a KPM source that reduces one slice's effective capacity
   as a function of other slices' simultaneous ceilings/load (unlike
   `ClosedLoopKpmSource`'s fully independent per-slice model) --
   ideally calibrated against E4's own already-measured live coupling
   (embb's 6.6-13.1-point degradation under urllc's presence) rather
   than invented. Given Stage 12's finding that no synthetic KPM source
   in this project's history has yet been validated against live
   *dynamics* (only mean-matched), the more defensible path is
   validating any new source's per-step behavior against a live capture
   before trusting checkpoints trained on it -- itself real rig time,
   not a training-side-only fix.
3. **Revalidation, not just retraining.** Per Stage 12's own explicit
   conclusion, a retrained checkpoint's offline convergence quality
   would still carry "close to zero information" about live behavior
   until the environment fix above is itself live-validated -- so even
   after retraining, a checkpoint would need a live smoke-test pass
   before being trusted as PF2-1's actual pilot arm, not just a fresh
   offline training run substituted in place of the current one.

This is a genuine retraining-plus-revalidation cycle, not a config
tweak available before an already-scheduled pilot. Per the milestone's
own closing framing, this is the kind of finding that feeds a
supervisor timeline/rescoping decision, not one to resolve unilaterally
here.

## STOP

GATE PF2-0: **train/eval mismatch, not reward-design isolation.** Per
the milestone's explicit instruction, NOT proceeding to PF2-1 (the live
pilot) on the current checkpoints/config. Awaiting go/direction:
whether to scope and execute the retraining-plus-revalidation cycle
above before any live pilot, or to make a different call on M45's
scope/timeline given this finding.
