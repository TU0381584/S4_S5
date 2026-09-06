#!/usr/bin/env python3
"""M44-C: does the PRB-ceiling surface have a real, GRADED shed region
above the 5-PRB scheduler floor?

At a chosen sustained offered load (real open-ceiling demand a few PRB
above the floor, per M44-A's own measured curve -- NOT the milestone's
example bitrate, which was calibrated against an assumption that doesn't
match this rig's actual measured urllc/mmtc demand curves), sweeps the
target slice's ceiling (pinned min=max=ratio, a direct E2 write, no policy
running) in fine steps from above-demand down to the 5-PRB floor (and one
step below, to see the collapse edge for contrast). At each step, captures:

  - served throughput + loss, from the UE-side iperf3 client's own -i 1
    interval reports (it is the RECEIVER here, since traffic uses
    --reverse) -- NOT avg_prbs_dl, which saturates at the 5-PRB
    observability floor exactly as this milestone's own instruction warns.
  - RLC's own bounded-buffer reject count and tx_size/tx_maxsize, from the
    M43DBG rlc_am_recv_sdu instrumentation already built into the current
    binary (M43's own real, active drop-mechanism instrument, reused
    as-is here) -- attributed to the target slice by taking the entity
    pointer with the most recv_sdu calls in each step's window, since the
    other two slices are held at low/native load throughout.
  - dl_mac_buffer_occupation, via the existing probe_e2_preconditions.py
    tool (unmodified).
  - RLC max-RETX events, cumulative, from the UE's own console log.

Never touches min_rbSize or any committed config. New logic only. Writes
to experiments/results/m44c/ only.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44c"

# Calibrated from M44-A's OWN measured curve (experiments/results/m44/
# demand_curve_{slice}.jsonl), not the milestone's example bitrate, which
# assumed urllc's demand at 50x/15Mbps would be ~8-12 PRB -- it's actually
# ~100 PRB (near carrier saturation) per M44-A's direct measurement.
# Interpolating M44-A's own two nearest bracketing points instead:
#   urllc: 10x=7.00 PRB, 20x=19.27 PRB -> target ~9-10 PRB needs ~12x
#   mmtc:  50x=7.07 PRB, 100x=18.53 PRB -> target ~9-10 PRB needs ~58-60x
CALIBRATED_MULT = {"urllc": 12.0, "mmtc": 60.0}

N_RB_SCHED_INIT = 106
MIN_RBSIZE = 5


def raw_prbs(ratio_pct: float) -> int:
    return int((N_RB_SCHED_INIT * ratio_pct) // 100)


def set_ceiling(sst: int, sd: int, min_ratio: int, max_ratio: int) -> None:
    cmd = (f"cd {RIG}/framework && {RIG}/venv/bin/python3 -m "
           f"qoe_oran_framework.scripts.probe_e2_preconditions "
           f"--send-control --sst {sst} --sd {sd} --min-ratio {min_ratio} --max-ratio {max_ratio} "
           f"--polls 1 --interval-s 0.1")
    r = m41.sh(cmd, timeout=30)
    print(f"[m44c] set ceiling sst={sst} sd={sd} min={min_ratio} max={max_ratio}: rc={r.returncode}",
          file=sys.stderr)


def launch_reporting_traffic(slice_id: str, bitrate_kbps: float, ue_ip: str, ns: str | None,
                              log_path: Path) -> subprocess.Popen:
    info = m44a.SLICE_TRAFFIC[slice_id]
    prefix = f"sudo ip netns exec {ns} " if ns else "sudo "
    # stdbuf -oL forces line-buffered stdout on iperf3 itself (redirected to
    # a file, iperf3's own libc stdio is fully block-buffered by default --
    # M44-D found this the hard way: a tight ~15s sampling cadence read the
    # log before the first flush and got None/stale readings for the first
    # 40+ seconds of every cold-start run). Harmless for a longer-running
    # sweep like this one's callers too; only affects I/O timeliness, not
    # the traffic itself.
    cmd = (f"{prefix}stdbuf -oL -eL iperf3 -c {m44a.TARGET_CONTAINER_IP} -p {info['port']} -B {ue_ip} "
           f"-u -b {bitrate_kbps}K -l {info['packet_len']} --reverse -i 1 -t 3600")
    fh = open(log_path, "w")
    proc = subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    time.sleep(2)
    return proc


# iperf3 auto-scales the rate's unit prefix (K/M/G) per-line depending on
# the actual instantaneous rate -- an earlier run of this script naively
# treated the numeric value as always-Kbits regardless of the printed
# unit, silently under-reporting "served" by up to 1000x whenever iperf3
# printed Mbits/sec. Fixed: capture the unit letter and convert to Kbps.
#
# SECOND bug found after that fix: at a genuine zero-throughput interval
# (a real, total outage) iperf3 prints NO prefix letter at all --
# "0.00 Bytes  0.00 bits/sec" -- so both \wBytes and ([KMG])bits/sec
# failed to match, and these true-collapse lines were silently dropped
# entirely. parse_recent_intervals() then fell back to the last line it
# COULD match, which during a sustained outage is stale pre-collapse
# data -- producing the internally-contradictory "served~3400Kbps,
# loss=0.0%" readings alongside independently-measured 100% RLC
# rejection. Fixed by making the prefix optional in both places and
# mapping the empty prefix to bits/sec's own scale (0.001 Kbps/unit).
#
# Also: iperf3's own per-interval "Lost/Total" loss% is 0/0 (0%) when
# the receiver got literally nothing in that interval (no sequence
# numbers arrived to detect a gap against) -- so loss_pct reads 0% even
# during a total outage. Don't trust loss_pct alone; compare served_kbps
# against the row's own offered_kbps to see the real shortfall.
INTERVAL_RE = re.compile(
    r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+\w?Bytes\s+([\d.]+)\s+([KMG]?)bits/sec\s+"
    r"[\d.]+\s+ms\s+(\d+)/(\d+)\s+\((\-?[\d.]+)%\)"
)
UNIT_TO_KBPS = {"": 0.001, "K": 1.0, "M": 1000.0, "G": 1000000.0}


def parse_recent_intervals(log_path: Path, last_n_seconds: float) -> dict:
    """Parse the tail of an iperf3 -i1 client log for recent per-second
    interval lines (receiver side, since --reverse). Returns mean received
    kbits/sec (unit-corrected) and mean loss pct over the requested
    trailing window."""
    if not log_path.exists():
        return {"mean_kbps": None, "mean_loss_pct": None, "n_intervals": 0}
    lines = log_path.read_text(errors="ignore").splitlines()
    rates, losses = [], []
    for line in lines[-200:]:
        m = INTERVAL_RE.search(line)
        if not m:
            continue
        start_s = float(m.group(1))
        rate_kbps = float(m.group(3)) * UNIT_TO_KBPS[m.group(4)]
        loss_pct = float(m.group(7))
        rates.append((start_s, rate_kbps, loss_pct))
    if not rates:
        return {"mean_kbps": None, "mean_loss_pct": None, "n_intervals": 0}
    cutoff = rates[-1][0] - last_n_seconds
    recent = [r for r in rates if r[0] >= cutoff]
    if not recent:
        recent = rates[-3:]
    mean_kbps = sum(r[1] for r in recent) / len(recent)
    mean_loss = sum(r[2] for r in recent) / len(recent)
    return {"mean_kbps": mean_kbps, "mean_loss_pct": mean_loss, "n_intervals": len(recent)}


def parse_rlc_am_stats(gnb_log_path: Path, window_start_line: int) -> dict:
    """Reads M43DBG rlc_am_recv_sdu lines appended since window_start_line,
    groups by entity pointer, returns the busiest entity's own
    tx_size/tx_maxsize/sdu_rejected trajectory (last sample) and the
    fraction of calls in this window that were rejected -- attributed to
    the target slice by "busiest entity in this window" (see module
    docstring). Also returns the new line count, for the next window's
    start point."""
    if not gnb_log_path.exists():
        return {"entities": {}, "next_line": window_start_line}
    all_lines = gnb_log_path.read_text(errors="ignore").splitlines()
    new_lines = all_lines[window_start_line:]
    per_entity = {}
    for line in new_lines:
        if "M43DBG rlc_am_recv_sdu" not in line:
            continue
        em = re.search(r"entity=(0x[0-9a-f]+)", line)
        tx_size_m = re.search(r"tx_size=(-?\d+)", line)
        tx_max_m = re.search(r"tx_maxsize=(-?\d+)", line)
        rej_m = re.search(r"sdu_rejected=(-?\d+)", line)
        this_rej_m = re.search(r"rejected_this_sdu=(\d+)", line)
        if not (em and tx_size_m and tx_max_m and rej_m and this_rej_m):
            continue
        ent = em.group(1)
        d = per_entity.setdefault(ent, {"n": 0, "n_rejected": 0, "last_tx_size": 0,
                                         "last_tx_maxsize": 0, "last_sdu_rejected": 0})
        d["n"] += 1
        d["n_rejected"] += int(this_rej_m.group(1))
        d["last_tx_size"] = int(tx_size_m.group(1))
        d["last_tx_maxsize"] = int(tx_max_m.group(1))
        d["last_sdu_rejected"] = int(rej_m.group(1))
    return {"entities": per_entity, "next_line": len(all_lines)}


def busiest_entity(entities: dict) -> dict:
    if not entities:
        return {"n": 0, "n_rejected": 0, "last_tx_size": 0, "last_tx_maxsize": 0, "last_sdu_rejected": 0}
    return max(entities.values(), key=lambda d: d["n"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True, choices=["urllc", "mmtc"])
    ap.add_argument("--offered-mult", type=float, default=None,
                     help="override the calibrated bitrate multiplier")
    ap.add_argument("--ceiling-ratios", type=float, nargs="+",
                     default=[20, 15, 12, 10, 9, 8, 7, 6, 5, 4])
    ap.add_argument("--settle-s", type=float, default=15.0)
    ap.add_argument("--sample-s", type=float, default=10.0)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slice_id = args.slice
    info = m44a.SLICE_TRAFFIC[slice_id]
    mult = args.offered_mult or CALIBRATED_MULT[slice_id]
    bitrate = info["native_bitrate_kbps"] * mult
    ts = time.strftime("%Y%m%d_%H%M%S")

    print(f"[m44c] === M44-C shed sweep: slice={slice_id} offered={mult}x native ({bitrate}Kbps) ===",
          file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44c] FATAL: docker core failed", file=sys.stderr)
        return 1
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return 1
    m41.start_traffic(1.0, ts)
    print("[m44c] traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)

    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44c] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    if not gate_ok:
        m41.teardown(None, ts)
        return 1

    m41.teardown(None, ts)
    if not m41.ensure_docker_core(force_fresh=True):
        return 1
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return 1
    m41.start_traffic(1.0, ts2)
    print("[m44c] post-gate fresh stack up, 30s settle...", file=sys.stderr)
    time.sleep(30)

    # Wide open first, to measure and record real open-ceiling demand at
    # the chosen offered load, per the milestone's own instruction.
    m44a.set_ceiling_wide_open(1, info["sd"])
    time.sleep(3)
    ue_ip, ns = m44a.get_ue_ip(slice_id)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    traffic_log = OUT_DIR / f"traffic_{slice_id}_{ts2}.log"
    traffic_proc = launch_reporting_traffic(slice_id, bitrate, ue_ip, ns, traffic_log)
    if traffic_proc.poll() is not None:
        print(f"[m44c] FATAL: traffic client failed to start", file=sys.stderr)
        m41.teardown(None, ts2)
        return 1
    print(f"[m44c] settling {args.settle_s}s at open ceiling before recording baseline demand...",
          file=sys.stderr)
    time.sleep(args.settle_s)

    baseline_demand = m44a.poll_demand(polls=15, interval_s=1.0)
    print("[m44c] OPEN-CEILING baseline demand:", file=sys.stderr)
    print(baseline_demand["stdout"][-1000:], file=sys.stderr)

    ue_log_names = {"urllc": "ue3", "mmtc": "ue2"}
    ue_log = RIG / f"experiments/logs/{ue_log_names[slice_id]}_m41_{ts2}.log"
    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"

    def retx_count() -> int:
        if not ue_log.exists():
            return 0
        return ue_log.read_text(errors="ignore").count("max RETX reached")

    results = []
    gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines()) if gnb_log.exists() else 0
    aborted = False
    try:
        for ratio in args.ceiling_ratios:
            ratio_int = int(ratio)
            print(f"[m44c] --- ceiling ratio={ratio_int}% (~{raw_prbs(ratio_int)} raw PRB) ---",
                  file=sys.stderr)
            set_ceiling(1, info["sd"], ratio_int, ratio_int)
            time.sleep(args.settle_s)

            retx_before = retx_count()
            time.sleep(args.sample_s)
            retx_after = retx_count()
            new_retx = retx_after - retx_before

            thr = parse_recent_intervals(traffic_log, args.sample_s)
            rlc = parse_rlc_am_stats(gnb_log, gnb_line_cursor)
            gnb_line_cursor = rlc["next_line"]
            busiest = busiest_entity(rlc["entities"])
            pct_rejected = (100.0 * busiest["n_rejected"] / busiest["n"]) if busiest["n"] else None

            demand_now = m44a.poll_demand(polls=8, interval_s=1.0)
            buf_occ_match = re.search(rf"sst1/sd{info['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%",
                                       demand_now["stdout"])
            buf_occ_pct = float(buf_occ_match.group(1)) if buf_occ_match else None

            row = {
                "slice": slice_id, "ceiling_ratio_pct": ratio_int, "ceiling_raw_prbs": raw_prbs(ratio_int),
                "served_kbps": thr["mean_kbps"], "iperf_loss_pct": thr["mean_loss_pct"],
                "offered_kbps": bitrate,
                "rlc_entity_calls_in_window": busiest["n"], "rlc_pct_rejected_in_window": pct_rejected,
                "rlc_tx_size": busiest["last_tx_size"], "rlc_tx_maxsize": busiest["last_tx_maxsize"],
                "rlc_sdu_rejected_cumulative": busiest["last_sdu_rejected"],
                "dl_mac_buffer_occupation_pct": buf_occ_pct,
                "new_max_retx_events": new_retx, "cumulative_max_retx": retx_after,
            }
            results.append(row)
            (OUT_DIR / f"sweep_{slice_id}.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44c]   served={thr['mean_kbps']}Kbps loss={thr['mean_loss_pct']}% "
                  f"rlc_rejected%={pct_rejected} buf_occ%={buf_occ_pct} new_retx={new_retx}",
                  file=sys.stderr)

            if new_retx > 50:
                print(f"[m44c] COLLAPSE detected ({new_retx} new max-RETX events) at ratio={ratio_int}%, "
                      f"restoring ceiling to safe value and stopping sweep", file=sys.stderr)
                set_ceiling(1, info["sd"], 18, 18)
                aborted = True
                break
    finally:
        traffic_proc.terminate()
        m41.teardown(None, ts2)

    print(f"[m44c] === DONE ({'ABORTED' if aborted else 'completed'}), {len(results)} steps, "
          f"results in {OUT_DIR / f'sweep_{slice_id}.jsonl'} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
