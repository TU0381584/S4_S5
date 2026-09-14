# M45-PF2-1a — clean embb confirmation + power calculation

LIVE, bounded: 6 new runs (DQN-QoE/DQN-SLA x seeds 258/259/260 --
MR2's remaining untested seeds from its 6-seed pool, 256-261), same
E4 co-located regime, cold-start, contention gate every run, fully
post-MR1/MR3c-fix stack. All 6 `ok=True` (316.0-317.4s). Results:
`experiments/results/m45_pf21/pf21a/`.

## embb: coherent-negative, confirmed

Combining MR3c's 4 clean embb correlations (seeds 256/257, precise
`t>=first_e2_apply_write` cutoff) with this block's 6 new ones (same
method, seeds 258/259/260):

| seed | arm | embb r (clean) |
|---|---|---|
| 256 | qoe | -0.007 |
| 257 | qoe | -0.824 |
| 258 | qoe | -0.757 |
| 259 | qoe | -0.204 |
| 260 | qoe | -0.889 |
| 256 | sla | +0.004 |
| 257 | sla | -0.282 |
| 258 | sla | -0.099 |
| 259 | sla | -0.065 |
| 260 | sla | -0.060 |

**9 of 10 negative** (the 10th, seed256/sla, is +0.004 -- negligible,
not a real contradiction). Magnitudes vary (weak -0.06 to strong
-0.89) but the SIGN is now coherent across both arms and all 3 new
seeds independent of the specific seeds MR3c happened to use. **GATE
answer: embb clean responsiveness sign is coherent-negative -- YES.**
Per this milestone's own gate logic, this does not trigger the STOP
branch.

## urllc: NOT coherent with MR4's predicted sign -- flagged before proceeding

Not asked for in this block's original scope, but computed the same
way for the same 6 runs (cheap, same log parse, and directly relevant
to whether MR4's expected-sign table is trustworthy going into
pre-registration):

| seed | arm | urllc r (clean) |
|---|---|---|
| 256 | qoe | +0.051 |
| 257 | qoe | **-0.975** |
| 258 | qoe | **-0.910** |
| 259 | qoe | **-0.862** |
| 260 | qoe | **-0.971** |
| 256 | sla | -0.016 |
| 257 | sla | +0.265 |
| 258 | sla | -0.083 |
| 259 | sla | -0.066 |
| 260 | sla | -0.186 |

**8 of 10 negative, including four very strong ones (-0.86 to -0.98)
-- MR4's predicted POSITIVE sign for urllc does not hold up against
this larger, cleaner sample.** All 3 new PF2-1a seeds show a clean,
strong negative sign in the qoe arm specifically, which is the
opposite of MR4's "raises its own ceiling as its own backlog rises"
derivation.

**This is reported plainly as a real finding, not smoothed over, and
it changes what should go into PF2-1b's pre-registration.** Re-
examining the mechanism MR4 relied on: `AdmissionGate.apply()`'s
reject branch does two things simultaneously -- it lowers the ceiling
AND (via `notify_rejected()`) removes that request's traffic from the
system rather than leaving it queued. A policy that rejects MORE when
`remainUEs` is ALREADY high is using admission throttling to prevent
further overload -- mechanically producing a NEGATIVE correlation
(more backlog -> lower ceiling) as the signature of CORRECT protective
behavior, not incorrect behavior. MR4's derivation assumed raising the
ceiling is the primary lever for relieving a slice's own backlog; this
data suggests the policy instead primarily uses REJECTION (ceiling
DOWN) as its protective lever for urllc specifically, which is an
equally reward-consistent (arguably more directly reward-consistent,
since accepting more when already congested also costs the shared
`congestion_term`/`cost` penalty) mechanism MR4 did not fully rule
out. **Both signs are defensible in principle for an admission-control
ceiling; the data now says which one this policy family actually
uses.**

**Recommendation for PF2-1b, not decided unilaterally here**: revise
urllc's pre-registered expected sign to NEGATIVE (same as embb, same
underlying mechanism -- admission-throttling-based protection), or
drop the per-slice-sign prediction from the pre-registration entirely
and pre-register only the shed-classification split (which does not
depend on resolving this ambiguity -- see below). Do not carry MR4's
original urllc-positive prediction into PF2-1b unrevised; it is not
supported by the evidence now available.

## Power calculation: SLA vs QoE, paired on PWC by seed

Combined MR3c (seeds 256/257) + PF2-1a (seeds 258/259/260), n=5
matched seed-pairs (same seed number trained under each reward mode --
different checkpoints, paired by seed as this project's own
established Monte-Carlo convention does for cross-arm comparisons):

| seed | QoE PWC | SLA PWC | diff (SLA-QoE) |
|---|---|---|---|
| 256 | 0.3199 | 0.7077 | 0.3878 |
| 257 | 0.4622 | 0.7086 | 0.2464 |
| 258 | 0.3426 | 0.5693 | 0.2267 |
| 259 | 0.3416 | 0.5702 | 0.2287 |
| 260 | 0.3334 | 0.5384 | 0.2051 |

mean diff = 0.2589, sd diff = 0.0735 (n=5), paired Cohen's d = 3.52,
paired t = 7.87 (df=4), **two-sided p = 0.0014**.

**Per this milestone's own explicit instruction, this is NOT
interpreted as a verdict.** This project has already seen an n-small
significant result of this exact shape collapse completely once
properly powered (Stage 3->10: p=0.0149 at small n -> p=1.0 at n=46,
CACS26/Paper-#4 history) -- a p this small at n=5 is a reason for more
scrutiny, not more confidence, especially since the shed CLASSIFICATION
itself (not just PWC's continuous score) is even more extreme: 5/5
qoe seeds `indiscriminate_failure`, 5/5 sla seeds `correct_shed`, zero
exceptions across two independently-collected sessions (pre- and
post-MR3c fix). A perfectly clean categorical split at n=5 is exactly
the kind of small-sample pattern that can look unbeatable and still
not survive a properly powered, held-out test.

**Required n, three ways** (paired two-sided t-test, alpha=0.05,
80% power, `n = ((z_a/2 + z_b) / d)^2`):

| effect-size assumption | d | n required |
|---|---|---|
| observed (n=5, untrusted per above) | 3.52 | 1 |
| conservative (observed halved) | 1.76 | 3 |
| very conservative (observed quartered, still "large" by convention) | 0.88 | 11 |

**Hard ceiling this project cannot exceed without new offline
training (out of scope, standing constraint): only 6 seeds exist per
arm in MR2's checkpoint pool (256-261), 5 already used.** Even the
"very conservative" n=11 exceeds this ceiling. Recommended plan,
constrained by what's actually available:

- **Primary powered sample (PF2-1c): all 6 seeds/arm (256-261)** --
  exceeds the "conservative" bar (n=3), short of "very conservative"
  (n=11), and is the maximum available without retraining. Seed 261
  (the one remaining untested seed) still needs a live run for both
  arms.
- **Independent replication batch**: since the checkpoint-seed pool is
  exhausted at 6, replicate via a DIFFERENT source of randomness this
  project already treats as independent -- a fresh `--seed`
  (eval_seed, controls the synthetic admission-request arrival
  process, per `m46_mr3_live_revalidate.py`'s own established
  convention that eval_seed is unrelated to and need not match the
  checkpoint's training seed) on the SAME 6 checkpoints per arm. This
  tests robustness to a different arrival-process realization, a
  genuinely independent perturbation, without requiring new training.

## GATE PF2-1a

**(1) embb clean responsiveness**: coherent-negative, confirmed (9/10,
independent of MR3c's specific seeds).

**(2) urllc**: NOT coherent with MR4's predicted sign -- coherently
negative instead (8/10), most plausibly reflecting admission-
throttling-based protection rather than ceiling-raising-based service.
Recommend revising the pre-registered urllc sign before PF2-1b locks
it in.

**(3) Required n**: all 6 available seeds/arm for the primary sample
(the ceiling of what exists without new training); replication via a
new eval_seed on the same 6 checkpoints, not new checkpoints.

Per this milestone's own gate logic (embb coherent -> does not trigger
the confound-STOP branch), this does not block proceeding -- but the
urllc sign finding is surfaced prominently because it directly affects
what PF2-1b would otherwise commit to writing down as pre-registered.

**STOP. Awaiting go before PF2-1b** -- specifically on whether to (a)
revise urllc's expected sign to negative in the pre-registration, (b)
drop the per-slice-sign prediction and pre-register only the
shed-classification split, or (c) investigate the sign question
further before locking anything.
