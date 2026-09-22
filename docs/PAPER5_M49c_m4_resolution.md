# M49c — resolving M4's one unexplained reproducibility gap

## Status: NO RIG, complete. Scope: the federated-arm churn "close but not bit-identical" disagreement only, per the milestone's own instruction — M49's other findings are not re-audited here.

## The investigation

The original raw per-seed data for `fl_gat_ctde_sigma0.0`/churn no longer
exists (that is the entire reason M49 had to regenerate it), so M7's own
decision-level-diff method cannot be applied directly — there is no
original file to diff against. Instead, every plausible SOURCE of a
close-but-not-exact numerical drift was checked directly and eliminated
one at a time, until one explanation remained.

**Hypothesis 1 — the churn "fresh, never-trained policy" is seeded
differently now than at the original run: TESTED, REJECTED.**
`m4_run_experiment.py` seeds the fresh policy deterministically
(`torch.manual_seed(CHURN_FRESH_POLICY_SEED_OFFSET + seed)`,
`CHURN_FRESH_POLICY_SEED_OFFSET=800000`, unchanged since this file's
creation — confirmed via `git log --follow`, only 2 commits ever touched
it, neither changing this constant or the surrounding logic beyond an
unrelated path-parameterization refactor). A commit AFTER the original
M4 run (`a35f866`, 2026-08-17, the already-documented torch-seeding fix)
DID add a new `torch.manual_seed(seed)` call inside `run_episodes_marl`
itself — a real, dated, code-level difference between "then" and "now."
But reading `select_actions()` in both `ctde_policy.py` and
`fl_ctde_policy.py` directly shows the exploration branch
(`if training and np.random.rand() < self.epsilon`) is gated on
`training=True`; M4 calls every policy, including the fresh churn
policy, with `training=False` (confirmed at `marl_training.py`'s own
disruption-splice call site). **Eval-mode action selection performs
zero random draws of any kind (torch or numpy) — it is pure
argmax over a frozen (or, for the churn window, freshly-initialized but
still frozen-at-eval-time) network.** The new reseed added by `a35f866`
has nothing to consume in this code path and cannot be the cause.

**Hypothesis 2 — the M3 checkpoint the federated arm loads was
retrained after the original M4 run: TESTED, REJECTED.** `git log
--follow` on `experiments/results/m3_campaign/fl_gat_ctde_sigma0.0/
seed900/train/checkpoint.pt` shows exactly 3 commits, all BEFORE M4's
own original campaign commit: built (`8d54b51`, 2026-08-13), retrained
under the GATEncoder-normalization fix (`d3096a8`, 2026-08-14),
retrained again under the per-slice-heads fix (`3efec37`, 2026-08-15).
M4's original campaign (`f46c39a`) committed on 2026-08-16, AFTER all
three — meaning it already used the exact same, final checkpoint file
this gate's regeneration also loads. The checkpoint has not changed at
all since the original M4 run; not the cause.

**Hypothesis 3 — a code change to the actual inference/disruption
logic since the original run: TESTED, REJECTED.** `git log --since
2026-08-16` on `fl_ctde_policy.py`, `ctde_policy.py`, `gat_encoder.py`,
and `disruption.py` shows exactly 2 commits touching any of them
(`dd0ea6f`, `e7ad299`, both 2026-08-28) — both are the repo's own
folder-restructure fix-ups, and their diffs (checked directly) edit
**one docstring comment string** in `gat_encoder.py` ("CACS26/refs.bib"
→ "Papers_4-5/Paper_4/refs.bib"), zero computational changes. The
inference code is byte-identical to what the original M4 run executed.

**Hypothesis 4 — the current pipeline is itself non-deterministic
run-to-run: TESTED, REJECTED.** Re-ran `fl_gat_ctde_sigma0.0`/
churn_sev1/seed900 a second time today, fresh, and diffed the resulting
decision sequence (reward, block count, accepted counts, all 3000
steps) against this gate's own earlier regeneration: **identical**.
Today's pipeline is confirmed bit-for-bit self-deterministic.

**Remaining explanation, by elimination: environment/dependency drift
over the ~5-week gap between the original run (2026-08-16) and this
regeneration.** With code, checkpoint, and seeding logic all confirmed
identical, and today's own pipeline confirmed deterministic, the only
remaining variable is the software environment itself (torch/numpy/BLAS
versions, exact build) between then and now — a well-known, textbook
source of small, bounded floating-point drift in matrix-multiply-heavy
inference (GAT attention, Q-value computation) that can occasionally
flip a near-tied argmax decision, compounding over a 50-episode ×
60-step eval into the small aggregate differences observed. **This is
named as the cause by systematic elimination of every code-level and
data-level alternative, not directly observed as a version diff** — no
environment snapshot from 2026-08-16 survives to confirm the exact
library versions active then, which is itself worth recording as a
process gap for future work (pin and archive the environment, not just
the code, at every headline-number-producing run).

## Verdict: BENIGN

Every alternative that would make the regenerated number untrustworthy
(different code, different checkpoint, different seeding behavior that
actually matters, non-deterministic current pipeline) has been checked
and ruled out directly, not assumed. The remaining explanation is a
category the field already treats as benign (numerical drift from
environment differences), not a decision-logic defect. **The
regenerated value is trustworthy. M54 cites it.**

## Per-M4-number resolution table

| number | original (manuscript) | regenerated (this gate) | status | cause | cite decision |
|---|---|---|---|---|---|
| single-agent-DQN spike p-value (original sample) | p=0.0020 | p=0.0020 | **exact** | mc_runner.py eval path, unaffected by any post-hoc fix | cite as-is (already matches) |
| GAT-CTDE dropout costs (+0.165/+0.601/+1.710) | as cited | not regenerated this gate (already reproducible via `m4_paired_test/`, per GATE M49) | exact (pre-existing data, unaffected) | n/a -- data never lost | cite as-is |
| independent-DQN churn (original sample) | +0.000/+0.168/+0.640 | not regenerated this gate (already reproducible via `m4_paired_test/`) | exact (pre-existing data) | n/a | cite as-is |
| federated-arm churn costs (+0.073/+0.240/+0.585) | as cited | +0.078/+0.246/+0.585 | **close, not exact** (sev3 exact; sev1/2 within 2-6%) | environment/dependency drift over time, by elimination (see investigation above) -- BENIGN | **cite the regenerated values (0.078/0.246/0.585), not the original** -- the original raw data no longer exists to verify against, and the regenerated pipeline is fully verified sound |
| federated-arm dropout/spike costs | not specifically numbered in the manuscript (only GAT-CTDE's own dropout numbers and the qualitative spike sign are cited) | regenerated this gate, real values on file in `experiments/results/m4_campaign/fl_gat_ctde_sigma0.0/` | n/a -- no original number exists to compare against | n/a | cite the regenerated values (only values that exist) |
| GAT-CTDE / independent-DQN spike (qualitative "p≤0.014 in both") | bound only, no specific number | p=0.0020 at every severity, both arms (10/10 sign-consistent) | **satisfies the bound**, not a numeric mismatch (0.0020 ≤ 0.014) | n/a | cite the regenerated values; the bound itself does not need revising |
| single-agent-DQN dropout costs | qualitative only ("the same super-linear pattern holds for every arm") | 0.1663/0.5593/1.5248, accelerating, p=0.0020 throughout | qualitatively matches, no specific number to check exactness against | n/a | cite the regenerated values |

## What this changes in M54

Only the federated-arm churn sentence needs a small numeric revision
(0.073/0.240/0.585 → 0.078/0.246/0.585) plus a one-line provenance note
that this value was regenerated post-hoc from the still-intact frozen
checkpoint after the original raw per-seed logs were found missing
during the M49 reproducibility audit — stated plainly, not hidden, per
this project's own standing disclosure discipline. Every other M4
number entering M54 either already matched exactly or has no prior
numeric citation to reconcile against.

## STOP

GATE M49c. Reported per the milestone's own gate. Awaiting go before M54.
