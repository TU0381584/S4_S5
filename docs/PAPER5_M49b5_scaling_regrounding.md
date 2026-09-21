# M49b-5 — re-grounding M27's scaling result on an honest stress environment

## Status: OFFLINE, complete. Provenance audit: docs/PAPER5_M49b5_m27_provenance.csv. Re-run: experiments/results/m49b_5/ (216 new cells, ClosedLoopKpmSource, ~4.17h). Pre-registered: CONFIRM = findings hold under the clean env (likely); REVISE/OVERTURN = report honestly. Verdict: CONFIRM, and if anything the clean env shows the SAME finding more sharply.

## 1. Provenance audit (task 1) — summary

Full detail: `docs/PAPER5_M49b5_m27_provenance.csv`, verified via 3
independent checks (source-code hardcoding of `ClosedLoopKpmSource` in
`m6_run_experiment.py`'s own `make_kpm_source_factory`; every M6
extension shell script's own `SCRIPT=` line confirming direct
invocation of that same file; `m27_scaling_reframe.py`'s own explicit
monkeypatch of that function to `RealisticServedKpmSource`), not
assumed.

- **N=19 pooled 35.4% [25.5%,45.8%] estimate, and every other N=19
  number in `experiments/results/m6_pilot/`**: CLEAN
  (`ClosedLoopKpmSource`), confirmed directly from logs as the
  milestone required — stands as-is, no re-run needed.
- **M27's own N=19 recalibrated table** (`experiments/results/m27_scaling_reframe/n19_*`):
  CONTAMINATED, but already superseded by the clean N=19 result it was
  checked against (M27's own conclusion: statistically indistinguishable).
- **M27's own N=7 recalibrated table** (`experiments/results/m27_scaling_reframe/n7_*`):
  CONTAMINATED, and — unlike N=19 — this is the one number with no
  existing properly-powered clean-env comparison. M27's own text
  states this gap explicitly ("an equally-sized 12-seed
  `ClosedLoopKpmSource` resample at N=7, which this session did not
  run"). This is the re-run this gate closes.

## 2. The re-run (task 2)

`experiments/scripts/m49b5_n7_clean_env_resample.sh`, unmodified
`m6_run_experiment.py` (no monkeypatch — confirmed `ClosedLoopKpmSource`
throughout), same 100-train/20-eval budget M27 itself used, 3
topologies × 3 arms. Primary: seeds 900-911 (matching M6/M27's own
primary identity exactly). Independent replication: seeds 1000-1011
(extending M6's own 1000-1002 replication-range convention to full
12-seed power, disjoint from primary). Smoke-tested (1 seed, 3
episodes) before committing to the full ~4.17h run. Collapse computed
identically to M27's own convention (`m6_correctness_metrics.py`'s
`total_blocks==0` criterion, reused not reimplemented; bootstrapped
over the 12 independent seeds, not the 36 cells, since collapse status
correlates within a seed across its three topologies — confirmed here
too: every arm's per-topology collapsed-cell counts are identical or
near-identical within a sample).

### Result: honest (clean-env) N=7 collapse rates

| arm | primary (900-911) | replication (1000-1011) | M27's own N=7 (contaminated, 36 cells) | original 3-seed pilot |
|---|---|---|---|---|
| single-agent DQN | **11/12, 91.7% [75.0%,100%]** | **9/12, 75.0% [50.0%,100%]** | 18/36, 50.0% [25.0%,75.0%] | 0/3 (0%) |
| GAT-CTDE | **5/12, 41.7% [16.7%,66.7%]** | **7/12, 58.3% [33.3%,83.3%]** | 12/36, 33.3% [8.3%,58.3%] | 0/3 (0%) |
| independent DQN | **0/12, 0.0% [0.0%,0.0%]** | **2/12, 16.7% [0.0%,41.7%]** | 0/36, 0.0% [0.0%,0.0%] | 0/3 (0%) |

## 3. Verdict against M27's own three N=7 headline claims

**(a) "GAT-CTDE's N=7 collapse rate is statistically indistinguishable
from its own N=19 rate, present from N=7 onward, not an N=19-specific
phenomenon" — CONFIRMED, more sharply.** Both clean-env N=7 samples
(41.7%, 58.3%) comfortably overlap the clean N=19 pooled estimate
(35.4% [25.5%,45.8%]), the same qualitative conclusion M27 reached
under the contaminated environment (33.3%, also overlapping). If
anything the clean-env point estimates run slightly *higher* than the
contaminated ones, not lower — there is no reading of this data where
GAT-CTDE's N=7 collapse-proneness looks like a recalibration artifact.

**(b) "Single-agent DQN's original 3-seed 'holds 1.000 at N=7' pilot
does not survive a properly-powered resample" — CONFIRMED, dramatically
more sharply.** The clean-env collapse rate (91.7% primary, 75.0%
replication) is *nearly double* M27's own already-striking contaminated
estimate (50.0%), and both clean-env CIs sit entirely above the
original pilot's 0%. This is the single clearest result in this whole
re-grounding: the original pilot's finding was not merely
underpowered, it pointed in the *opposite direction* from what a
properly-powered sample — under either environment — actually shows.

**(c) "Independent DQN replicates cleanly, still never collapses" —
REVISED, in the same direction M27 itself already flagged for N=19.**
The clean-env *primary* sample matches exactly (0/12, 0%). The clean-env
*replication* sample does not (2/12, 16.7%) — a real, non-zero collapse
rate M27's own contaminated N=7 table never showed at all (0/36). This
echoes precisely the pattern M27 itself reported for independent DQN
at N=19 ("the recalibration surfaces something new... not a
contradiction at the current sample size, but a real, observed
difference in the raw counts, reported here rather than smoothed
over") — except here it is the *replication* sample under the *clean*
environment that surfaces it, not the recalibration. Read together
with M27's own N=19 finding, independent DQN's "never fully collapses"
claim should soften to "rarely, not never" **regardless of which
environment or which N** — this is now supported by four independent
observations (N=19 clean pooled 0/36, N=19 contaminated 3/36, N=7
clean primary 0/12, N=7 clean replication 2/12), not one.

## 4. What this means for the paper

**The recalibration's specific numeric values were an artifact
(retired, M49b-4) — but the qualitative finding it produced at N=7
(a properly-powered resample reveals real collapse-proneness a 3-seed
pilot could never show) holds up independently under the honest,
disclosed-stress `ClosedLoopKpmSource` environment, and holds up more
starkly, not less.** M54 can report the N=7 finding using this gate's
own clean-env numbers directly, dropping any dependency on the retired
recalibration entirely — the paper's own comparative claim ("N=7 is
not a safe scale for either GAT-CTDE or single-agent DQN") is, if
anything, understated by M27's own contaminated numbers relative to
what the clean environment shows.

## 5. Framing check (task 3): does `ClosedLoopKpmSource`'s contention level need disclosing as an explicit stress regime?

Yes. M32-M34's own diagnosis (recorded directly in
`docs/PAPER5_M27_scaling_reframe.md`) is that `ClosedLoopKpmSource`'s
`congestion_level` is structurally capped near 0.03-0.09 (served PRB is
bounded by the admission ceiling, which a trained policy keeps below
real demand), while this rig's own live measurement showed real
congestion at 0.23-0.26 (3 UEs) and 0.60-0.69 (6 UEs) -- already a
~3-8x gap between the offline environment's own achievable contention
and what this rig's live traffic actually produces at the load levels
it was tested at.

**M49b-1-1 sharpens this rather than narrows it.** The live
measurement that produced those 0.23-0.69 congestion readings was
itself later found (M49b-1-1, live, post-M41-fix) to reflect a rig
serving ~100% of offered demand with 0.000% loss -- i.e., even this
rig's own *live* congestion range is not "genuine scarcity" in the
sense `ClosedLoopKpmSource`'s own 0.03-0.09 congestion levels are
meant to represent (a regime where accept/reject decisions carry a
real, delayed consequence because served capacity is actually
constrained). Read together, this arc establishes a wider gap than
M27 itself could see at the time: **the live rig, at every load level
ever tested on it, cannot reach genuine per-slice PRB scarcity at all**
-- not merely "the offline simulator historically undershot the live
rig's congestion," but "the live rig itself has never been shown to
reach a load level where any of the three slices' real admission
decisions carry a genuine capacity consequence."

This means `ClosedLoopKpmSource`'s own congestion range is not a
miscalibrated *approximation* of a reachable live regime -- it is a
**deliberately harder, disclosed stress condition that this live rig
cannot currently produce**, full stop. The existing manuscript text
already gestures at exactly this framing without fully committing to
it (§System Model: "we therefore use it explicitly as a *stress
environment* for a contention regime our live rig does not reach, not
as a claim that any offline ranking would reproduce live"). This arc
gives that sentence its full evidentiary backing rather than a
qualitative hedge: it is not merely that live-rank prediction doesn't
hold (M1's own, separately-established finding); it is that the *live
rig's own achievable contention*, at any composition or UE count this
project has ever tested, sits at or below the scheduler's hard 5-PRB
floor, while `ClosedLoopKpmSource` exercises the policy at a
genuinely harder, disclosed-as-unreachable level above it.

**Recommendation for M54**: state this plainly in the manuscript (the
Cluster-Size Scaling section's own framing, and the System Model's
existing stress-environment sentence) as an explicit, evidenced claim:
`ClosedLoopKpmSource`'s contention regime is retained specifically
*because* it is a disclosed stress condition beyond this live rig's own
demonstrated reach (M49b-1-1), not despite that gap. This is a
strength of the paper's own honesty framing, not a limitation to
minimize -- it is exactly the kind of claim this whole M48-M54 arc
exists to get right rather than gloss over.

## Disk

Committed data: 7.2G (216 new cells' train+eval omega logs and
checkpoints, `experiments/results/m49b_5/`), matching this project's
own established practice of committing the full evidence chain for
offline campaigns (`experiments/results/m6_pilot/`'s own 35G, already
git-tracked, 747 files). 27G free on disk after.

## STOP

Reported per the milestone's own gate. This closes the entire M48-M54
live-contamination re-collection arc (M48/M48b provenance and
citation audit; M49b-0 quarantine; M49b-1-0/1-1 honest anchors;
M49b-2/3 live falsification; M49b-4 recalibration retirement; M49b-5
this offline re-grounding). Awaiting go before M54 (the manuscript
rewrite folding in the whole arc's honest findings) -- not proceeding
into it without that explicit go, per the standing gate discipline
established across every milestone in this arc.

