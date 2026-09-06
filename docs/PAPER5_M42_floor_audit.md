# M42: config-floor integrity audit (GATED — G1 report)

Standing constraints honored throughout: no edits to frozen `qoe_oran_framework`
source or any committed config/result — this pass is read-only forensics plus
one new script (`experiments/scripts/m42_floor_matrix.py`), no rig work. M41's
applied fix (`saclb_live.yaml`) is untouched. No old-rig data reused. Every
number below is either directly computed/quoted from a cited source or marked
`TODO(MEASURE)` — none invented.

## G1-A: which config backs which published number

Resolved via script/doc/log ground truth, not filename assumption, per the
task's own instruction. Full evidence trail in `manifest.csv`.

**Paper #4 (CACS26), Stage 15 N128 campaign** — confirmed four independent
ways (orchestration script's hardcoded `CFG_OF` mapping, `docs/REPRODUCIBILITY.md`'s
explicit provenance table, `docs/STAGE15_n128_campaign.md`'s narrative, and the
omega logs' own recorded `ceilings` values matching each config's ratios
exactly):

| Arm | Config |
|---|---|
| baseline ("Static") | `saclb_campaign_baseline_v2.yaml` |
| static_at_cap | `saclb_campaign_static_at_cap_v2.yaml` |
| dqn_sla | `saclb_campaign_v2.yaml` |
| dqn_qoe | `saclb_campaign_v2.yaml` (same file as dqn_sla) |

**Paper #5 (WPC), Fig. 8** — already resolved in `docs/PAPER5_FIG8_validity_check.md`:
all three live-anchor cells (original@3UE, original@6UE, recalibrated@6UE) use
`experiments/configs/saclb_campaign.yaml`.

**Paper #5 (WPC), M8 live single-gNB anchor** — `framework/qoe_oran_framework/configs/saclb_live.yaml`,
but critically at its **pre-M41-fix ratios** (in place 2026-07-16 through
2026-09-05, spanning M8's entire run window per git history) — the file has
since been fixed (commit `cda9d65`) and no longer reflects what M8 actually ran
under.

## G1-B: the floor matrix

`experiments/results/m42_floor_audit/config_floor_matrix.csv`, computed by
`experiments/scripts/m42_floor_matrix.py`. Conversion cited directly from
source: `raw_prbs = (n_rb_sched_init * ratio_pct) // 100` (integer division,
`gNB_scheduler_dlsch.c:1526-1528,1556`); `n_rb_sched_init=106` confirmed
empirically via M41's own live instrumentation (not a config value); the
scheduler's hard minimum grant, `min_rbSize=5`, is the specific occurrence at
`gNB_scheduler_dlsch.c:1075` inside `pf_dl_slice()` (the two other textually
identical `min_rbSize=5` occurrences at lines 880/1333 do not gate real
scheduling the same way — see `docs/PAPER5_M41_envelope_sweep.md`).

**Headline result: urllc and mmtc are BROKEN (cap raw PRBs < 5) in every
single config/campaign row audited, with zero exceptions** — Paper #4's all
four arms, Paper #5's Fig. 8 all three cells, and Paper #5's M8 anchor (both
runs). embb is MARGINAL (floor below 5, cap above it) in every `_v2`/campaign
config and in M8's pre-fix config (where even embb's cap, 4 raw PRB, was
BROKEN) — only the current, already-fixed `saclb_live.yaml` shows OK (floor=6)
across all three slices.

| Config family | embb | urllc | mmtc |
|---|---|---|---|
| `saclb_campaign*_v2.yaml` (Paper #4, all 4 arms) | MARGINAL (floor=1,cap=12) | **BROKEN** (cap=4) | **BROKEN** (cap=3) |
| `saclb_campaign.yaml` (Fig. 8, all 3 cells) | MARGINAL (floor=1,cap=12) | **BROKEN** (cap=4) | **BROKEN** (cap=3) |
| `saclb_live.yaml` pre-fix (M8, both runs) | **BROKEN** (cap=4) | **BROKEN** (cap=3) | **BROKEN** (cap=3) |
| `saclb_live.yaml` post-fix (M41, current) | OK (floor=6) | OK (floor=6) | OK (floor=6) |

## G1-C: forensics from the original historical logs

**Paper #4's N128 campaign**: no raw gNB/UE console logs survive from the
campaign window (checked: nothing under `experiments/logs/` with a
July-31-to-Aug-4 modification time). The campaign's own health-check
(`health_check.sh`) never tested for RLC max-RETX at all, and its
`PROGRESS.log` shows zero restart/unhealthy events across the whole
run — but this is not evidence of health, since the check was never designed
to catch this specific signature. The omega logs' own `limitation` field
**explicitly states, for every slice, every step**: `"dl_mac_buffer_occupation
was 0 for all UEs; used (dl_errors + dl_bler) as a backlog proxy for L_k(t)"`
— meaning the `per_slice_sla_margin`/`per_slice_compliant` fields the
campaign's headline compliance numbers are built from are **not a direct
measurement of real RLC-layer health**; they're a proxy that was already known,
at the time, to be running on a degraded fallback. Whether real backlog on
urllc/mmtc ever demanded more than a below-floor ceiling could serve: **cannot
be determined from surviving artifacts — `TODO(MEASURE)`.**

**Fig. 8's cells**: found candidate raw console logs (`live_ue2..6_console.log`)
showing 60,000+ real `max RETX reached` events each, onset within the first
2.5% of each file — but each file's filesystem birth time (2026-08-19) does not
match its last-modified time (2026-08-27), an internally inconsistent
provenance that makes it unsafe to attribute these specific logs to the exact
Fig.8-cited `6ue_20ep` run (completed 12:31) versus a separate, later
`6ue_2hr` stress run (completed ~14:48) without further reconstruction work
not attempted here. **Treated as inconclusive**, not used to support either
verdict. The one piece of **direct, unambiguous, already-existing live
evidence** remains Part 3C's own reproduction: the actual original checkpoint
against the real, unmodified `saclb_campaign.yaml`, at native ("3UE") load,
failed at t=10.0s with 19 real `max RETX reached` events on urllc.

## GATE G1 verdict

**Cannot be cleanly classified into (a), (b), or (c) from existing artifacts.**
Specifically:

- **Not (a)**: urllc was confirmed live and controlled in Fig.8's cells (Part
  3C's live ceiling-value match); Paper #4's campaign's own recorded live
  `ceilings` fields show urllc/mmtc receiving real per-step control writes in
  every arm.
- **Leaning against (b)** for Fig.8 specifically: Part 3C's direct live
  reproduction using the actual original checkpoint and the actual unmodified
  config failed within 10 seconds — the below-floor ceiling was NOT provably
  inert. For Paper #4, whether backlog ever bound the ceiling is genuinely
  unknown (no surviving direct telemetry).
- **Not confirmed (c)** either, since "still healthy" cannot be verified
  independently of the same degraded-proxy metric that's in question — the
  compliance numbers those episodes report may not be sensitive to the failure
  mode at all, which would make "healthy by this metric" uninformative rather
  than reassuring.

**Recommendation: proceed to G2.** Static forensics has been pushed as far as
surviving artifacts allow; the config-floor violation is confirmed, universal,
and severe (not just Fig.8 — Paper #4's entire submitted 128-episode campaign
and M8's foundational live anchor share the identical structural flaw), but
whether it actually manifested as real, uncompensated RLC failure during those
specific historical runs cannot be settled without a live reproduction under
the *original* harness (`run_live_eval_arm.py` + `traffic_profiles.yaml`), per
G2's own design — not the M41 iperf3 harness, which G1 confirms is a
methodological difference, not yet ruled out as the reason Part 3C's quick
verification failed while the historical runs apparently didn't.

**One scope note for G2, not decided here**: this audit surfaces that G2's
originally-scoped target (Fig.8's "Original, 3UE" cell only) may be too narrow
— Paper #4's entire N128 campaign and M8's anchor share the identical
BROKEN/MARGINAL exposure. Awaiting direction on whether G2 should also cover
at least one Paper #4 arm and/or M8, or stay scoped to Fig.8 as originally
written, before proceeding.
