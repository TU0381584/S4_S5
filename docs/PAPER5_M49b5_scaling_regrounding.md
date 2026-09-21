DRAFT IN PROGRESS -- results section pending the M49b-5 N=7 clean-env
resample (experiments/scripts/m49b5_n7_clean_env_resample.sh), running
in the background. This file will be completed and this notice removed
once that run finishes. The framing-check section below (task 3) does
not depend on the resample's outcome and is final.

## Framing check (task 3): does ClosedLoopKpmSource's contention level need disclosing as an explicit stress regime?

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

---

[RESULTS SECTION PENDING -- see experiments/results/m49b_5/ once the
background resample completes.]
