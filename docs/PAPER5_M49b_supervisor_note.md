# Note for Pang/Phang — WPC's Live Single-gNB Anchor section is under re-collection, not withdrawn

## What was found

The M48 scope-lock audit (`docs/PAPER5_M48_scope_map.csv`) inventoried
every result behind the WPC manuscript before any rewrite. Following
that up with a live-provenance check (`docs/PAPER5_M48b_provenance_audit.csv`)
found that the entire Live Single-gNB Anchor section — §"Live
Single-gNB Anchor" and both of its subsections, "Heavier Live Load"
and "Recalibrating the Simulator to Match Live Congestion" — was
collected under `saclb_live.yaml` between 2026-07-16 and 2026-08-19,
before a scheduler-floor bug in the live control loop was found and
fixed (M41, 2026-09-05). Under the pre-fix config, all three slices'
commanded ceiling ranges sit below the gNB scheduler's hard 5-PRB
grant minimum — the same structural defect M42's audit separately
found in Paper #4's own submitted campaign config. The manuscript's
own headlined "fix" result (the RealisticServedKpmSource recalibration
that reverses a complete 6-UE collapse) is itself affected: both the
anchors it was built from and its own live confirmation run predate
the scheduler-floor fix.

## What this does and does not mean

This is **not** a claim that the section's findings are wrong. A
below-floor config can produce results that turn out to still hold
once re-collected correctly, results that need revising, or results
that were entirely an artifact of the bug and should be retracted —
each of the three outcomes is a legitimate, reportable result in its
own right, and overturning a floor-bug artifact is the correct outcome
of this check, not a failure of the check. What the finding does mean
is that **none of this section's numbers can currently be trusted as
representative of the system's real behaviour**, since the mechanism
that would explain any anomaly (the floor bug) was active and
unaccounted for throughout.

## What has been done already (no rig, this pass)

1. Every affected claim in `Papers_4-5/Paper_5/WPC/main.tex` is now
   marked with a visible, in-text flag (`PRE-FIX DATA -- DO NOT SUBMIT`)
   at the abstract's live-anchor sentence, the Introduction's
   live-transfer promise, and the start of all three affected sections
   — the underlying text is untouched, only flagged, since it is the
   re-collection target, not something to delete pre-emptively.
2. The three citations to Paper #4's own compliance-survives-correction
   headline (a separate, independent problem — Paper #4's own
   submitted config was separately found below the scheduler floor,
   M42) have been rewritten to keep only what that paper's own
   companion-submission relationship still supports honestly: the E2
   control loop's feasibility and latency, and the lightweight model's
   parameter count. This citation fix stands regardless of how #5's
   own re-collection turns out.
3. The manuscript still compiles cleanly (26 pages, `pdflatex` +
   `bibtex`, no undefined references or citations) with these flags in
   place, so it remains a complete, readable draft — just one that
   cannot currently be submitted, by design.

## The plan (bounded, gated, live rig work not yet started)

A 5-step re-collection plan is scoped and pre-registered
(`M49b-1` through `M49b-5`, not yet run): re-derive honest,
non-artifact served-capacity anchors for the affected slices; re-run
the decision-transfer anchor and the 3-vs-6-UE load campaign under the
fixed config; separately re-test the recalibration's own premise and
live benefit against a same-checkpoint control; and re-run the offline
topology re-run (M27) that reused the same contaminated anchors. Each
step has its own pre-registered CONFIRM/REVISE/OVERTURN criteria,
decided before any run, and each stops for review before the next
begins.

**#5 is not to be submitted until this re-collection completes.** This
note is the issue and the plan, not a conclusion — the actual outcome
of each step will be reported as it happens, honestly, whichever way
it goes.
