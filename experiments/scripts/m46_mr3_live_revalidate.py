#!/usr/bin/env python3
"""M46-MR3 -- THE TRUST GATE: live-revalidate MR2's retrained checkpoints
at the E4 co-located regime (urllc 3600Kbps/12x + embb 12000Kbps/3x,
mmtc native), cold-start, running the REAL live policy control loop
(frozen qoe_oran_framework/xapp/saclb_xapp.py, unmodified) instead of
this project's own fixed-ceiling send_control calls -- unlike M44-E4,
which manually pinned ceilings to characterize the regime, here the
CHECKPOINT itself must make live E2 ceiling decisions against real,
E4-coupled radio state.

Reuses M44's already-verified live-rig machinery directly (imported, not
reimplemented): m41_envelope_sweep (bring-up/teardown/gate/traffic),
m44_scarcity_probe (UE IP/ns, demand poll, iperf3-target recreate),
m44c_shed_sweep (reporting-traffic launch, corrected interval parser,
RLC AM stats parser), m44e_coldstart (embb traffic launch/SLICE_INFO),
m44e2b_ceiling_bind_check (M41DBG ceiling+postpf parser),
m44e4_colocation_sweep (genuine NSSAI/rnti/entity resolution -- not a
busiest-entity heuristic). PWC/shed-classification reused unmodified
from m45_priority_weighted_correctness.py.

Unlike E4's live-sample-then-sleep loop (used because ceilings were
externally fixed and steady-state took time to settle), this script lets
saclb_xapp.py run to completion (one full episode, ~300s) and then parses
the COMPLETE resulting gNB log + traffic logs post-hoc, binned into
SAMPLE_INTERVAL_S windows for PWC (matching E4's own convention) and at
native M41DBG sample granularity for the state-responsiveness
correlation (a coarse 15s-window mean would wash out the moment-to-moment
action/state relationship this check specifically needs).

Cold-start discipline preserved: fresh docker-core + native-stack cycle,
contention gate, PER RUN (never shared/reused across checkpoints) --
identical rigor to every prior M44/M45 live milestone. Never touches
min_rbSize/tx_maxsize/frozen source. Never widens the action space
(saclb_xapp.py is called against the SAME MR1 config, unedited).
"""
import json
import re
import statistics as stats
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44c_shed_sweep as m44c
import m44e_coldstart as m44e
import m44e2b_ceiling_bind_check as m44e2b
import m44e4_colocation_sweep as m44e4
import m45_priority_weighted_correctness as pwc

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m46_mr3"
CONFIG = RIG / "experiments/configs/m46/saclb_m46_train.yaml"
XAPP_SCRIPT = RIG / "framework/qoe_oran_framework/xapp/saclb_xapp.py"
FRAMEWORK_DIR = RIG / "framework"
CKPT_ROOT = RIG / "experiments/results/m46_mr2/offline_train"

URLLC = m44a.SLICE_TRAFFIC["urllc"]
EMBB = m44e.SLICE_INFO["embb"]
URLLC_MULT = 12.0   # 3600 Kbps -- M44-D's own band-producing load
EMBB_MULT = 3.0     # 12000 Kbps -- M44-E2b's own band-producing load

SAMPLE_INTERVAL_S = 15.0     # PWC window size, matches E4's own convention
EPISODES_PER_RUN = 1         # one 300s episode per checkpoint -- trust check, not the powered campaign
XAPP_TIMEOUT_S = 420.0       # 300s episode + E2 connection/startup margin

# In-band expectation, from MR1's own static verification (config_band_alignment.csv)
EXPECTED_RANGE = {"urllc": {6, 7, 8}, "embb": {5, 6, 7, 8, 9, 10}}

# (reward_mode, training_seed, eval_seed) -- 2 checkpoint-seeds per arm,
# per this milestone's own "2-3 seeds per arm, trust check not powered
# campaign" instruction. eval_seed is saclb_xapp.py's OWN --seed (controls
# the synthetic per-step admission-request arrival RNG on top of live KPM
# -- unrelated to, and not required to match, the checkpoint's training
# seed), reusing this project's established "eval seeds start at 950"
# convention, one per run so no two runs share an identical arrival
# sequence.
RUNS = [
    ("qoe", 256, 950),
    ("qoe", 257, 951),
    ("sla", 256, 952),
    ("sla", 257, 953),
]


def checkpoint_path(mode: str, seed: int) -> Path:
    return CKPT_ROOT / mode / f"seed{seed}" / "dqn" / "offline_closed_loop" / "rep_0" / "checkpoint.pt"


def parse_all_intervals(log_path: Path):
    """Like m44c.parse_recent_intervals but returns EVERY matched interval
    (start_s, rate_kbps, loss_pct), not just a trailing-window mean --
    needed here to bin the whole run into windows post-hoc rather than
    live-poll a trailing window. Reuses the exact same corrected regex/
    unit table, not a re-derived parser."""
    if not log_path.exists():
        return []
    out = []
    for line in log_path.read_text(errors="ignore").splitlines():
        m = m44c.INTERVAL_RE.search(line)
        if not m:
            continue
        start_s = float(m.group(1))
        rate_kbps = float(m.group(3)) * m44c.UNIT_TO_KBPS[m.group(4)]
        loss_pct = float(m.group(7))
        out.append((start_s, rate_kbps, loss_pct))
    return out


def bin_mean(pairs, lo, hi, value_idx):
    vals = [p[value_idx] for p in pairs if lo <= p[0] < hi]
    return float(stats.mean(vals)) if vals else None


def pearson(xs, ys):
    """Plain Pearson r, no numpy dependency. Returns None if undefined
    (fewer than 3 points or zero variance in either series) -- never
    silently returns 0.0 for an undefined case."""
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return None, len(pts)
    xv = [p[0] for p in pts]
    yv = [p[1] for p in pts]
    if stats.pstdev(xv) == 0 or stats.pstdev(yv) == 0:
        return None, len(pts)
    mx, my = stats.mean(xv), stats.mean(yv)
    cov = sum((x - mx) * (y - my) for x, y in pts) / len(pts)
    r = cov / (stats.pstdev(xv) * stats.pstdev(yv))
    return r, len(pts)


def state_responsiveness(ceiling_rows, postpf_rows, sid):
    """Direct action-vs-state correlation for one slice: live commanded
    ceiling (M41DBG 'ceiling' max_prbs) vs live backlog/pending-UE count
    (M41DBG 'postpf' remainUEs), both from the gNB's own scheduler state,
    independent of anything saclb_xapp.py itself observed. Computed at
    native M41DBG sample granularity (NOT the coarser PWC window), since
    a 15s-window mean would wash out the moment-to-moment relationship
    this check needs. Reports contemporaneous (lag=0) and a modestly
    lagged (lag=5 samples, backlog leading ceiling) correlation, since a
    real controller may react with a short delay rather than instantly."""
    ceil = sorted([r for r in ceiling_rows if r["sid"] == sid], key=lambda r: r["t"])
    post = sorted([r for r in postpf_rows if r["sid"] == sid], key=lambda r: r["t"])
    n = min(len(ceil), len(post))
    ceil, post = ceil[:n], post[:n]
    max_prbs = [r["max_prbs"] for r in ceil]
    remain_ues = [r["remainUEs"] for r in post]

    r0, n0 = pearson(remain_ues, max_prbs)
    lag = 5
    if n > lag:
        r_lag, n_lag = pearson(remain_ues[:-lag], max_prbs[lag:])
    else:
        r_lag, n_lag = None, 0
    return {
        "n_samples": n,
        "pearson_r_contemporaneous": r0, "n_contemporaneous": n0,
        "pearson_r_lag5": r_lag, "n_lag5": n_lag,
        "max_prbs_distinct_values": sorted(set(max_prbs)),
        "remainUEs_range": [min(remain_ues), max(remain_ues)] if remain_ues else None,
    }


def run_one(mode: str, train_seed: int, eval_seed: int, run_idx: int, total: int,
            algorithm: str = "dqn", config_override: Path = None,
            checkpoint_override: Path = None, reward_mode_override: str = None) -> dict:
    """M47-PF2-1c extension (backward compatible: every prior caller
    passes only the first 5 positional args, unaffected): algorithm/
    config_override/checkpoint_override let this same cold-start/gate/
    traffic/parsing pipeline run the 3 non-learning PF2-1c arms
    (static-at-cap, static-at-floor, lb_only) alongside the DQN arms,
    without duplicating any of the surrounding live-rig machinery.
    algorithm="lb_only" needs no checkpoint (mirrors saclb_xapp.py's
    own argparse: --checkpoint required unless --algorithm lb_only)."""
    if checkpoint_override is not None:
        ckpt = checkpoint_override
    elif algorithm == "dqn":
        ckpt = checkpoint_path(mode, train_seed)
        assert ckpt.exists(), f"missing checkpoint: {ckpt}"
    else:
        ckpt = None
    cfg_path = config_override if config_override is not None else CONFIG
    run_id = f"m46mr3_{mode}_seed{train_seed}"
    print(f"[m46-mr3] === run {run_idx}/{total}: {run_id} (eval_seed={eval_seed}) === "
          f"COLD START urllc=3600Kbps/12x embb=12000Kbps/3x mmtc=native", file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        return {"mode": mode, "train_seed": train_seed, "error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(time.strftime("%Y%m%d_%H%M%S")):
        m41.teardown(None, time.strftime("%Y%m%d_%H%M%S"))
        return {"mode": mode, "train_seed": train_seed, "error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, time.strftime("%Y%m%d_%H%M%S"))
    print("[m46-mr3] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(time.strftime("%Y%m%d_%H%M%S"))
    print(f"[m46-mr3] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, time.strftime("%Y%m%d_%H%M%S"))
    if not gate_ok:
        return {"mode": mode, "train_seed": train_seed, "error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"mode": mode, "train_seed": train_seed, "error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"mode": mode, "train_seed": train_seed, "error": "bringup_failed_phase2"}

    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    buf_urllc_m = re.search(rf"sst1/sd{URLLC['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
    buf_embb_m = re.search(rf"sst1/sd{EMBB['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
    pre_buf = {"urllc": float(buf_urllc_m.group(1)) if buf_urllc_m else None,
               "embb": float(buf_embb_m.group(1)) if buf_embb_m else None}
    print(f"[m46-mr3] pre-traffic buffer occupation: {pre_buf}", file=sys.stderr)

    urllc_ip, urllc_ns = m44a.get_ue_ip("urllc")
    embb_ip, embb_ns = m44a.get_ue_ip("embb")
    m41.start_traffic(1.0, ts2)
    time.sleep(2)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {URLLC['port']}")
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {EMBB['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    urllc_log = OUT_DIR / f"traffic_urllc_{mode}_seed{train_seed}_{ts2}.log"
    embb_log = OUT_DIR / f"traffic_embb_{mode}_seed{train_seed}_{ts2}.log"
    urllc_bitrate = URLLC["native_bitrate_kbps"] * URLLC_MULT
    embb_bitrate = EMBB["native_bitrate_kbps"] * EMBB_MULT
    urllc_proc = m44c.launch_reporting_traffic("urllc", urllc_bitrate, urllc_ip, urllc_ns, urllc_log)
    embb_proc = m44e.launch_traffic("embb", embb_bitrate, embb_ip, embb_ns, embb_log)
    if urllc_proc.poll() is not None or embb_proc.poll() is not None:
        print("[m46-mr3] FATAL: traffic client failed to start", file=sys.stderr)
        urllc_proc.terminate(); embb_proc.terminate()
        m41.teardown(None, ts2)
        return {"mode": mode, "train_seed": train_seed, "error": "traffic_launch_failed"}

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    line_cursor_start = len(gnb_log.read_text(errors="ignore").splitlines()) if gnb_log.exists() else 0

    omega_path = OUT_DIR / mode / f"seed{train_seed}" / "omega_log.jsonl"
    omega_path.parent.mkdir(parents=True, exist_ok=True)
    xapp_console_log = OUT_DIR / f"xapp_console_{mode}_seed{train_seed}_{ts2}.log"

    xapp_cmd = [
        str(RIG / "venv/bin/python3"), str(XAPP_SCRIPT),
        "--config", str(cfg_path), "--algorithm", algorithm,
    ]
    if ckpt is not None:
        xapp_cmd += ["--checkpoint", str(ckpt)]
    xapp_cmd += [
        "--gnb-id", "gnb-0",
        "--episodes", str(EPISODES_PER_RUN), "--seed", str(eval_seed),
        "--run-id", run_id, "--omega-jsonl", str(omega_path),
        "--reward-mode", (reward_mode_override if reward_mode_override is not None else mode),
    ]
    print(f"[m46-mr3] launching live policy loop: {' '.join(xapp_cmd)}", file=sys.stderr)
    t0 = time.time()
    xapp_ok = True
    with open(xapp_console_log, "w") as fh:
        try:
            result = subprocess.run(xapp_cmd, cwd=str(FRAMEWORK_DIR), stdout=fh, stderr=subprocess.STDOUT,
                                     timeout=XAPP_TIMEOUT_S)
            xapp_ok = (result.returncode == 0)
        except subprocess.TimeoutExpired:
            xapp_ok = False
            print("[m46-mr3] FATAL: saclb_xapp.py timed out", file=sys.stderr)
    elapsed = time.time() - t0
    print(f"[m46-mr3] xapp finished in {elapsed:.1f}s, ok={xapp_ok}", file=sys.stderr)

    urllc_proc.terminate()
    embb_proc.terminate()

    if not xapp_ok:
        m41.teardown(None, ts2)
        return {"mode": mode, "train_seed": train_seed, "error": "xapp_run_failed",
                "console_log": str(xapp_console_log)}

    # Post-hoc parse over the WHOLE run window, not a live sample loop.
    sd_to_entity = m44e4.resolve_slice_entities(gnb_log)
    print(f"[m46-mr3] resolved sd->entity: {sd_to_entity}", file=sys.stderr)
    rlc = m44c.parse_rlc_am_stats(gnb_log, line_cursor_start)
    m41dbg = m44e2b.parse_m41dbg(gnb_log, line_cursor_start)
    urllc_ptr = sd_to_entity.get(URLLC["sd"])
    embb_ptr = sd_to_entity.get(EMBB["sd"])
    urllc_rlc = rlc["entities"].get(urllc_ptr, {"n": 0, "n_rejected": 0})
    embb_rlc = rlc["entities"].get(embb_ptr, {"n": 0, "n_rejected": 0})

    urllc_intervals = parse_all_intervals(urllc_log)
    embb_intervals = parse_all_intervals(embb_log)

    n_windows = max(1, int(elapsed // SAMPLE_INTERVAL_S))
    trajectory = []
    for i in range(n_windows):
        lo, hi = i * SAMPLE_INTERVAL_S, (i + 1) * SAMPLE_INTERVAL_S
        urllc_maxprbs_w = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 3 and lo <= (r["t"] - m41dbg["ceiling_rows"][0]["t"]) < hi] if m41dbg["ceiling_rows"] else []
        embb_maxprbs_w = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 1 and lo <= (r["t"] - m41dbg["ceiling_rows"][0]["t"]) < hi] if m41dbg["ceiling_rows"] else []
        mmtc_maxprbs_w = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 2 and lo <= (r["t"] - m41dbg["ceiling_rows"][0]["t"]) < hi] if m41dbg["ceiling_rows"] else []

        def _mean(xs):
            return sum(xs) / len(xs) if xs else None

        row = {
            "window_idx": i, "window_lo_s": lo, "window_hi_s": hi,
            "urllc_served_kbps": bin_mean(urllc_intervals, lo, hi, 1), "urllc_offered_kbps": urllc_bitrate,
            "urllc_loss_pct": bin_mean(urllc_intervals, lo, hi, 2),
            "urllc_rlc_rej_pct": (100.0 * urllc_rlc["n_rejected"] / urllc_rlc["n"]) if urllc_rlc["n"] else None,
            "urllc_m41dbg_maxprbs_mean": _mean(urllc_maxprbs_w),
            "embb_served_kbps": bin_mean(embb_intervals, lo, hi, 1), "embb_offered_kbps": embb_bitrate,
            "embb_loss_pct": bin_mean(embb_intervals, lo, hi, 2),
            "embb_rlc_rej_pct": (100.0 * embb_rlc["n_rejected"] / embb_rlc["n"]) if embb_rlc["n"] else None,
            "embb_m41dbg_maxprbs_mean": _mean(embb_maxprbs_w),
            "mmtc_m41dbg_maxprbs_mean": _mean(mmtc_maxprbs_w),
        }
        trajectory.append(row)
        (OUT_DIR / mode / f"seed{train_seed}" / "trajectory.jsonl").open("a").write(json.dumps(row) + "\n")

    urllc_inband = {v for v in {r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 3}}
    embb_inband = {v for v in {r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == 1}}

    urllc_resp = state_responsiveness(m41dbg["ceiling_rows"], m41dbg["postpf_rows"], sid=3)
    embb_resp = state_responsiveness(m41dbg["ceiling_rows"], m41dbg["postpf_rows"], sid=1)

    pwc_result = pwc.compute_pwc_for_trajectory(trajectory)

    result = {
        "mode": mode, "train_seed": train_seed, "eval_seed": eval_seed, "run_id": run_id,
        "checkpoint": (str(ckpt) if ckpt is not None else None), "algorithm": algorithm,
        "config": str(cfg_path), "elapsed_s": elapsed, "ts2": ts2,
        "pre_traffic_buffer": pre_buf, "sd_to_entity": sd_to_entity,
        "urllc_maxprbs_observed": sorted(urllc_inband), "urllc_in_band": urllc_inband.issubset(EXPECTED_RANGE["urllc"]) and len(urllc_inband) > 0,
        "embb_maxprbs_observed": sorted(embb_inband), "embb_in_band": embb_inband.issubset(EXPECTED_RANGE["embb"]) and len(embb_inband) > 0,
        "urllc_state_responsiveness": urllc_resp, "embb_state_responsiveness": embb_resp,
        "pwc": pwc_result, "trajectory": trajectory,
    }
    m41.teardown(None, ts2)
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[m46-mr3] === M46-MR3 live revalidation: {len(RUNS)} (mode, train_seed) runs = {RUNS} ===",
          file=sys.stderr)
    all_results = []
    for idx, (mode, train_seed, eval_seed) in enumerate(RUNS, 1):
        res = run_one(mode, train_seed, eval_seed, idx, len(RUNS))
        all_results.append(res)
        (OUT_DIR / "all_runs.json").write_text(json.dumps(all_results, indent=2))
    print(f"[m46-mr3] === DONE, {len(all_results)} runs, results in {OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
