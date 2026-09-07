#!/usr/bin/env python3
"""M44-E4: can urllc and embb be simultaneously inside their own confirmed
realistic graded bands under ONE live multi-slice offered load, and can
distinct per-slice ceilings be independently expressed?

urllc's band: 6-8 raw PRB at 3600 Kbps (12x native) -- M44-D.
embb's band: 5-10 raw PRB at 12000 Kbps (3x native) -- M44-E2b.
mmtc is excluded (no realistic band, E1b) and is left at its own native
background traffic throughout, same as every prior contention-gate
methodology in this project.

Cold-start discipline: BOTH ceilings are set before either slice's
elevated traffic exists on the connection -- never wide-open, never
ratcheted. For each (urllc_ceiling, embb_ceiling) combination:
  1. contention gate on a throwaway stack
  2. fresh restart
  3. both ceilings fixed
  4. both buffers confirmed drained
  5. both slices' elevated traffic launched simultaneously (urllc at
     3600Kbps/12x, embb at 12000Kbps/3x -- their own individual
     band-producing loads, run together, not new loads invented for
     this milestone)
  6. >=120s hold, sampling BOTH slices' served/loss (corrected parser)
     and BOTH slices' own RLC AM SDU-reject stats (attributed by
     genuine RNTI->entity resolution read fresh from this run's own
     log, not a busiest-entity heuristic -- with two slices elevated
     simultaneously a heuristic could misattribute) and BOTH slices'
     live M41DBG scheduler max_prbs (already-built-in instrumentation,
     reused from M44-E2b unmodified).

Combinations: a baseline co-location point, then a two-phase sweep
(hold embb ceiling mid-band and vary urllc across its band, then hold
urllc mid-band and vary embb across its band) to test whether the two
slices can be independently, simultaneously controlled.

Never touches min_rbSize, tx_maxsize, or committed config/frozen
source. New logic only. Writes to experiments/results/m44e4/ only.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44c_shed_sweep as m44c
import m44e_coldstart as m44e
import m44e2b_ceiling_bind_check as m44e2b

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44e4"

URLLC = m44a.SLICE_TRAFFIC["urllc"]
EMBB = m44e.SLICE_INFO["embb"]
URLLC_MULT = 12.0   # 3600 Kbps -- urllc's own confirmed band-producing load (M44-D)
EMBB_MULT = 3.0     # 12000 Kbps -- embb's own confirmed band-producing load (M44-E2b)

HOLD_S = 120.0
SAMPLE_INTERVAL_S = 15.0

# (urllc_ceiling, embb_ceiling). Run 1 is the baseline co-location check.
# Runs 2-3 vary urllc with embb held mid-band (phase A). Runs 4-6 vary
# embb with urllc held mid-band (phase B, "the swap").
COMBOS = [
    (6, 7),
    (7, 7),
    (8, 7),
    (7, 5),
    (7, 8),
    (7, 10),
]

RNTI_INGRESS_RE = re.compile(r"M43DBG rlc_ingress t=[\d.]+ rnti=(\d+)")
RLC_AM_RE = re.compile(r"M43DBG rlc_am_recv_sdu t=[\d.]+ entity=(0x[0-9a-f]+)")
NSSAI_MATCH_RE = re.compile(r"exact NSSAI match \(\d+:0x([0-9a-f]+)\)", re.IGNORECASE)
UE_CTX_RE = re.compile(r"Created new UE context: CU UE ID (\d+) DU UE ID (\d+)")


def resolve_slice_entities(gnb_log_path: Path) -> dict:
    """Maps NSSAI sd -> RLC AM entity pointer, read fresh from this run's
    own log (never hardcoded): NSSAI-match order gives sd -> CU UE ID,
    'Created new UE context' gives CU UE ID -> rnti, and the first
    rlc_ingress(rnti=X)/rlc_am_recv_sdu(entity=Y) adjacent pair for that
    rnti gives rnti -> entity. With two slices elevated simultaneously a
    busiest-entity heuristic could misattribute; this resolves both
    slices' own entities directly instead."""
    lines = gnb_log_path.read_text(errors="ignore").splitlines()

    cu_id_to_sd = {}
    next_cu = 1
    for line in lines:
        m = NSSAI_MATCH_RE.search(line)
        if m:
            cu_id_to_sd[next_cu] = int(m.group(1), 16)
            next_cu += 1

    cu_id_to_rnti = {}
    for line in lines:
        m = UE_CTX_RE.search(line)
        if m:
            cu_id_to_rnti[int(m.group(1))] = m.group(2)

    sd_to_rnti = {sd: cu_id_to_rnti[cu] for cu, sd in cu_id_to_sd.items() if cu in cu_id_to_rnti}

    rnti_to_entity = {}
    for i, line in enumerate(lines):
        m = RNTI_INGRESS_RE.search(line)
        if not m:
            continue
        rnti = m.group(1)
        if rnti in rnti_to_entity:
            continue
        for j in range(i + 1, min(i + 4, len(lines))):
            m2 = RLC_AM_RE.search(lines[j])
            if m2:
                rnti_to_entity[rnti] = m2.group(1)
                break

    return {sd: rnti_to_entity.get(rnti) for sd, rnti in sd_to_rnti.items()}


def run_one_combo(urllc_ceil: int, embb_ceil: int, run_idx: int, total: int) -> dict:
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m44e4] === run {run_idx}/{total}: COLD START urllc_ceiling={urllc_ceil} "
          f"embb_ceiling={embb_ceil} (urllc=3600Kbps/12x, embb=12000Kbps/3x, mmtc native) ===",
          file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m44e4] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44e4] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "bringup_failed_phase2"}

    m44c.set_ceiling(1, URLLC["sd"], urllc_ceil, urllc_ceil)
    m44c.set_ceiling(1, EMBB["sd"], embb_ceil, embb_ceil)
    time.sleep(3)

    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    buf_urllc_m = re.search(rf"sst1/sd{URLLC['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%",
                             demand["stdout"])
    buf_embb_m = re.search(rf"sst1/sd{EMBB['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%",
                            demand["stdout"])
    pre_buf = {"urllc": float(buf_urllc_m.group(1)) if buf_urllc_m else None,
               "embb": float(buf_embb_m.group(1)) if buf_embb_m else None}
    print(f"[m44e4] pre-traffic buffer occupation: {pre_buf}", file=sys.stderr)

    urllc_ip, urllc_ns = m44a.get_ue_ip("urllc")
    embb_ip, embb_ns = m44a.get_ue_ip("embb")
    m41.start_traffic(1.0, ts2)  # native background -- mmtc stays native, urllc/embb replaced below
    time.sleep(2)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {URLLC['port']}")
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {EMBB['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    urllc_log = OUT_DIR / f"traffic_urllc_u{urllc_ceil}e{embb_ceil}_{ts2}.log"
    embb_log = OUT_DIR / f"traffic_embb_u{urllc_ceil}e{embb_ceil}_{ts2}.log"
    urllc_bitrate = URLLC["native_bitrate_kbps"] * URLLC_MULT
    embb_bitrate = EMBB["native_bitrate_kbps"] * EMBB_MULT
    urllc_proc = m44c.launch_reporting_traffic("urllc", urllc_bitrate, urllc_ip, urllc_ns, urllc_log)
    embb_proc = m44e.launch_traffic("embb", embb_bitrate, embb_ip, embb_ns, embb_log)
    if urllc_proc.poll() is not None or embb_proc.poll() is not None:
        print("[m44e4] FATAL: traffic client failed to start", file=sys.stderr)
        urllc_proc.terminate()
        embb_proc.terminate()
        m41.teardown(None, ts2)
        return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "error": "traffic_launch_failed"}

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    time.sleep(5)  # let both slices' SDUs flow so entity resolution can succeed
    sd_to_entity = resolve_slice_entities(gnb_log)
    print(f"[m44e4] resolved sd->entity: {sd_to_entity}", file=sys.stderr)

    gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines())
    samples = []
    aborted = False
    t0 = time.time()
    try:
        n_samples = int(HOLD_S // SAMPLE_INTERVAL_S)
        for i in range(n_samples):
            time.sleep(SAMPLE_INTERVAL_S)
            elapsed = time.time() - t0

            urllc_thr = m44c.parse_recent_intervals(urllc_log, SAMPLE_INTERVAL_S)
            embb_thr = m44c.parse_recent_intervals(embb_log, SAMPLE_INTERVAL_S)

            rlc = m44c.parse_rlc_am_stats(gnb_log, gnb_line_cursor)
            m41dbg = m44e2b.parse_m41dbg(gnb_log, gnb_line_cursor)
            gnb_line_cursor = rlc["next_line"]

            urllc_ptr = sd_to_entity.get(URLLC["sd"])
            embb_ptr = sd_to_entity.get(EMBB["sd"])
            urllc_rlc = rlc["entities"].get(urllc_ptr, {"n": 0, "n_rejected": 0})
            embb_rlc = rlc["entities"].get(embb_ptr, {"n": 0, "n_rejected": 0})
            urllc_rej_pct = (100.0 * urllc_rlc["n_rejected"] / urllc_rlc["n"]) if urllc_rlc["n"] else None
            embb_rej_pct = (100.0 * embb_rlc["n_rejected"] / embb_rlc["n"]) if embb_rlc["n"] else None

            urllc_maxprbs = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 3]
            embb_maxprbs = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 1]
            mmtc_maxprbs = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 2]

            def _mean(xs):
                return sum(xs) / len(xs) if xs else None

            row = {
                "urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil,
                "sample_idx": i, "elapsed_s": round(elapsed, 1),
                "urllc_served_kbps": urllc_thr["mean_kbps"], "urllc_offered_kbps": urllc_bitrate,
                "urllc_loss_pct": urllc_thr["mean_loss_pct"], "urllc_rlc_rej_pct": urllc_rej_pct,
                "urllc_m41dbg_maxprbs_mean": _mean(urllc_maxprbs),
                "embb_served_kbps": embb_thr["mean_kbps"], "embb_offered_kbps": embb_bitrate,
                "embb_loss_pct": embb_thr["mean_loss_pct"], "embb_rlc_rej_pct": embb_rej_pct,
                "embb_m41dbg_maxprbs_mean": _mean(embb_maxprbs),
                "mmtc_m41dbg_maxprbs_mean": _mean(mmtc_maxprbs),
            }
            samples.append(row)
            (OUT_DIR / f"trajectory_u{urllc_ceil}e{embb_ceil}.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44e4]   [u={urllc_ceil} e={embb_ceil} t={elapsed:.0f}s] "
                  f"urllc: served={row['urllc_served_kbps']}Kbps loss={row['urllc_loss_pct']}% "
                  f"rlc_rej%={urllc_rej_pct} maxprbs={row['urllc_m41dbg_maxprbs_mean']} || "
                  f"embb: served={row['embb_served_kbps']}Kbps loss={row['embb_loss_pct']}% "
                  f"rlc_rej%={embb_rej_pct} maxprbs={row['embb_m41dbg_maxprbs_mean']}",
                  file=sys.stderr)
    finally:
        urllc_proc.terminate()
        embb_proc.terminate()
        m41.teardown(None, ts2)

    return {"urllc_ceil": urllc_ceil, "embb_ceil": embb_ceil, "sd_to_entity": sd_to_entity,
            "pre_traffic_buffer": pre_buf, "samples": samples, "aborted": aborted, "ts2": ts2}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[m44e4] === M44-E4 co-location sweep: {len(COMBOS)} (urllc_ceiling, embb_ceiling) "
          f"combinations = {COMBOS} ===", file=sys.stderr)

    all_results = []
    for idx, (uc, ec) in enumerate(COMBOS, 1):
        result = run_one_combo(uc, ec, idx, len(COMBOS))
        all_results.append(result)
        (OUT_DIR / "all_runs.json").write_text(json.dumps(all_results, indent=2))

    print(f"[m44e4] === DONE, {len(all_results)} combinations tested, results in {OUT_DIR} ===",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
