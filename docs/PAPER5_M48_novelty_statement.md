# M48 — novelty statement candidates, against the #3 corpus (67 core studies) + named prior art

Every candidate below names the specific prior work it exceeds and the
specific evidence in this project that supports the claim, per the
task's own requirement. None of these is a final abstract sentence —
they are candidates for review before M54 commits to any of them.

## (i) First experimental realisation of #3's GAT-MARL-FL tier-3, with per-component measured contribution

#3's own conclusion places its proposed framework in a third,
"proposed but not-yet-validated" evidence tier, explicitly separate
from the 67 literature-validated studies and its own two preliminary
conference studies. Of the 67 studies in Tables 6-8, the handful that
combine two of #3's three pillars (Mohajer et al. 2026, Bouroudi et al.
2025, Qasim et al. 2025, Gong et al. 2026) each evaluate "exclusively
on its own reported outcome metric, computed once, on one seed or
run" — #3's own words. This project builds 4 of Table 12's 5
components (GAT encoder, MARL controller, FL coordinator, privacy
layer — the QoE mapper is M53's pending contribution) and reports a
measured, isolated contribution for each: GAT-CTDE's coordination
edge over an independent-learner ablation that shares the identical
per-agent input (+1.461 mean-reward/step, p<0.0001, 27/0/3 wins — M2),
federation's reward cost isolated from centralised training (+0.133,
n.s. — M3), and DP's utility cost isolated from clipping alone by
holding clip norm fixed and toggling only noise (a real, non-smooth
threshold at σ>1.0 — M3). No corpus study reports a comparably
component-isolated measurement.

## (ii) Correctness-aware evaluation exposing metric masking, replicated

**Exceeds**: Sulaiman et al. 2023/2024 (closest prior art — joint
slicing+admission MARL, no check on whether its own reward-optimal
policy could be scored no worse than a degenerate one by its own
reported metric) and every one of the 67 core studies, per #3's own
stated finding that "none... checks whether its own evaluation metric
can mask a degenerate policy." This project's `sla_compliance_all_slices`
metric scored a genuine training collapse (0/30 seeds ever blocking
anything) no worse than correct differentiated-shedding behaviour, and
disagreed with the correctness-aware pair (mean reward/step, block
precision) in 44/49 comparisons across M2/M3/M4/M6 (90%) — then an
independent supplementary batch on a disjoint seed range replicated
the disagreement rate at 21/24 (87.5%), combining to 44/49 (89.8%),
not a one-off finding on the sample that happened to surface it.

## (iii) Measured-anchor simulator recalibration, with the scaling finding surviving it

**Exceeds**: no corpus study recalibrates its own training environment
against real hardware measurements and then re-runs its headline
claim under the correction to check whether the claim was an artifact
of the uncorrected environment — the corpus's own gap analysis
(Table 9/10) names "validation is mostly simulation-based" as a
persistent, unaddressed gap across all 67 studies. This project's
`RealisticServedKpmSource` (anchored to real 3-UE/6-UE live
measurements, replacing a synthetic demand process whose congestion
range was shown to never exceed 0.09 against live's measured 0.23-0.69)
reverses a complete live policy collapse at 6 UEs (M8), and the
identical recalibration applied to the *offline* N=19/N=7 topology
campaign confirms the paper's own headline scaling finding (GAT-CTDE's
35.4% collapse rate) was not an artifact of the original simulator's
miscalibrated congestion range (M27) — closing Paper #4's own stated
future-work gap (validating the offline environment against measured
live SLA-margin magnitude) by a different, working mechanism than #4
itself proposed.

## (iv) Replication discipline catching a real architectural overclaim before publication

**Exceeds**: Tashman & Cherkaoui 2026 and Fatehi et al. 2026, both
disruption-robustness studies #3's own review cites as the closest
prior art to this project's own disruption campaign, neither of which
"checks whether the metric reporting that robustness is itself
trustworthy, or replicates a robustness finding on an independent
sample" (#3's own related-work framing, already in the current
manuscript). This project's own initial reading — that independent-DQN
is architecturally immune to agent churn, since it never attends to
another agent's features — looked confirmed on the committed seed
sample (p=0.065-0.106, borderline non-significant, read at the time as
supporting immunity) and was then directly contradicted by an
independent-seed replication (p=0.0020 at every severity, cost
*larger* than the coordinated arms') — retracted in the manuscript
itself rather than reported as the original, wrong reading. Of seven
headline paired comparisons checked this way across the whole paper,
this is the one exception; the other six hold up.

## (v) [pending M53] First multi-agent QoE-vs-SLA reward comparison under correctness-aware metrics

**Exceeds**: #3's own framework is explicitly QoE-aware end to end
(Table 12's QoE mapper feeding the MARL controller's reward), yet
neither #3's own two preliminary conference studies nor this project's
current GAT-CTDE line has a QoE-reward arm at the multi-gNB level —
Paper #4 established the QoE-vs-SLA comparison only for the
single-agent, single-gNB case. Once M53 runs (GAT-CTDE-QoE against
GAT-CTDE-SLA, same architecture/hyperparameters/seeds, differing only
in reward, on reward-agnostic correctness metrics with independent
replication before any claim), this would be the first place in either
the #3 corpus or this project's own line that the QoE-vs-SLA question
is asked under multi-agent coordination and correctness-aware metrics
together, rather than either alone. **This candidate is conditional on
M53's actual result** — it is a novelty claim about the *comparison
existing and being trustworthy*, not a claim about which reward wins,
and should not be finalised in the abstract until M53's GATE reports
back.

## Recommendation

(ii) and (iv) are the strongest candidates independent of any future
milestone — they rest entirely on work already done and already
gated. (i) and (iii) are strong but should be phrased carefully in
M54 to keep "first realisation" honestly scoped (4 of 5 components,
offline-only) rather than overclaiming full deployment validation,
per the binding positive-framing rule's own instruction to state
limits once, not smuggle them out of the headline claim. (v) should
stay a placeholder, not a committed sentence, until M53 reports.

## STOP

Reported per M48's own gate, alongside the scope map and contract map.
Awaiting review before any manuscript editing begins.
