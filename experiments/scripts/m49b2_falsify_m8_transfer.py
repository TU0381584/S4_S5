#!/usr/bin/env python3
"""M49b-2 -- falsify the M8 decision-transfer-under-load claim, post-fix.

PRE-REGISTERED (given by the milestone spec, not decided here):
  prediction = OVERTURN. With no real scarcity (M49b-1-1: all 3 slices
  serve ~100% of native demand below the 5-PRB scheduler floor), the
  original "differentiated shedding transfers live" reading should NOT
  reproduce as a contention-management result -- the policy runs, but
  there is nothing to differentiate because all slices are served
  regardless of decision.
  CONFIRM(overturn) = post-fix, blocks no longer track a scarcity
  signal / accepted+rejected requests both fully served.
  SURPRISE = genuine differentiated shedding still appears (escalate to
  a full campaign, report as a surprise, not force-fit to the
  prediction).

Runs the EXACT M8 seed-900 single-agent-DQN checkpoint, live, against
the SAME saclb_live.yaml the original M8 anchor used -- now carrying
the M41 floor fix (cda9d65) -- one clean documented run (a single-run
falsification, not a campaign, since the outcome is predicted; a
surprise is what would justify spending more rig time, not routine
confirmation).

NOTE, found only after a first attempt (eval_seed=3001, discarded --
its data is NOT used for this milestone's conclusion): reusing
m46_mr3_live_revalidate.run_one() unmodified silently runs at the
elevated E4 co-located regime (urllc 3600Kbps/12x, embb 12000Kbps/3x)
that entire script family hardcodes for the M45-M47 characterization
work, NOT M8's own native-traffic composition -- caught by noticing
the console log's own "COLD START urllc=3600Kbps/12x" line, not
assumed correct. M8's own claim is specifically about native,
unstressed traffic, so this file's own run_native_m8_style() mirrors
run_one()'s cold-start/gate/xapp-invocation/teardown structure exactly
but keeps native (1.0x) traffic for the whole run instead.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41  # noqa: E402
import m46_mr3_live_revalidate as mr3  # noqa: E402
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402
import m42_floor_matrix as m42  # noqa: E402 -- reusing its already-validated per-slice YAML parser

RIG = mr3.RIG
mr3.OUT_DIR = RIG / "experiments/results/m49b_2"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)

LIVE_CONFIG = RIG / "framework/qoe_oran_framework/configs/saclb_live.yaml"
CHECKPOINT = (RIG / "experiments/results/m8_live_anchor/offline_train/single_agent_dqn/"
              "seed900/train/dqn/offline_train/rep_0/checkpoint.pt")
EVAL_SEED = 3002  # 3001 was the discarded wrong-traffic-level attempt; new value, not reused


def verify_config_clears_floor(cfg_path: Path) -> bool:
    """Standing constraint: verify the applied config's ratios clear the
    5-PRB scheduler floor before ANY live run, abort if not. Reuses
    m42_floor_matrix's own already-validated per-slice YAML parser
    (splits on real '- slice_id:' list items) rather than an ad-hoc
    regex -- an earlier version of this check used a bare
    'slice_id:\\s*(\\w+)' pattern that also matched an unrelated code
    comment elsewhere in this same config file ('{s.slice_id: s for s
    in self.slices}'), silently consuming one real slice's match in the
    process. The numeric floor value it reported was still correct by
    coincidence (all three slices share the same floor in this config),
    but the mechanism was not reliably correct, and this is a safety
    check -- fixed before trusting it on any live run."""
    text = cfg_path.read_text()
    ok = True
    for slice_id, nominal, floor, cap in m42.parse_slices(text):
        raw_prbs = m42.raw_prbs(floor)
        status = "OK" if raw_prbs >= 5 else "BELOW FLOOR"
        print(f"[m49b2] {slice_id}: floor={floor}% -> {raw_prbs} raw PRB [{status}]", file=sys.stderr)
        if raw_prbs < 5:
            ok = False
    return ok


def run_native_m8_style(eval_seed: int) -> dict:
    """Mirrors m46_mr3_live_revalidate.run_one()'s own cold-start/gate/
    xapp-invocation/teardown structure exactly, EXCEPT the traffic level:
    run_one() always overrides urllc/embb to the elevated E4 regime
    (3600Kbps/12x, 12000Kbps/3x) after its own gate phase -- hardcoded,
    no parameter to disable it, confirmed by reading its source directly
    (found only AFTER a first, since-discarded run of this milestone
    reused run_one() unmodified and got E4-level contention instead of
    M8's own native composition -- caught by noticing the console log's
    own 'COLD START urllc=3600Kbps/12x' line, not assumed correct). M8's
    own original anchor used native traffic throughout (this is
    literally the thing M49b-2 is testing), so this function keeps
    native (1.0x) traffic for the ENTIRE run, gate phase and measurement
    phase alike -- the only other difference from run_one()."""
    run_id = f"m49b2_native_seed900"
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m49b2] === {run_id} (eval_seed={eval_seed}) === COLD START, NATIVE traffic all 3 slices "
          f"(NOT the E4-elevated regime run_one() would have used)", file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        return {"error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m49b2] gate-phase native traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m49b2] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"error": "bringup_failed_phase2"}

    m41.start_traffic(1.0, ts2)  # native for all 3 slices, held for the whole measurement phase
    time.sleep(5)

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    omega_path = mr3.OUT_DIR / "native" / "seed900" / "omega_log.jsonl"
    omega_path.parent.mkdir(parents=True, exist_ok=True)
    xapp_console_log = mr3.OUT_DIR / f"xapp_console_native_seed900_{ts2}.log"

    xapp_cmd = [
        str(RIG / "venv/bin/python3"), str(mr3.XAPP_SCRIPT),
        "--config", str(LIVE_CONFIG), "--algorithm", "dqn",
        "--checkpoint", str(CHECKPOINT),
        "--gnb-id", "gnb-0", "--episodes", "1", "--seed", str(eval_seed),
        "--run-id", run_id, "--omega-jsonl", str(omega_path),
        "--reward-mode", "sla",
    ]
    print(f"[m49b2] launching live policy loop: {' '.join(xapp_cmd)}", file=sys.stderr)
    t0 = time.time()
    with open(xapp_console_log, "w") as fh:
        try:
            result = subprocess.run(xapp_cmd, cwd=str(mr3.FRAMEWORK_DIR), stdout=fh,
                                     stderr=subprocess.STDOUT, timeout=mr3.XAPP_TIMEOUT_S)
            xapp_ok = (result.returncode == 0)
        except subprocess.TimeoutExpired:
            xapp_ok = False
            print("[m49b2] FATAL: saclb_xapp.py timed out", file=sys.stderr)
    elapsed = time.time() - t0
    print(f"[m49b2] xapp finished in {elapsed:.1f}s, ok={xapp_ok}", file=sys.stderr)
    m41.teardown(None, ts2)

    if not xapp_ok:
        return {"error": "xapp_run_failed", "console_log": str(xapp_console_log)}
    return {"error": None, "ts2": ts2, "omega_path": omega_path, "elapsed_s": elapsed}


def main() -> int:
    assert CHECKPOINT.exists(), f"missing checkpoint: {CHECKPOINT}"
    print(f"[m49b2] verifying {LIVE_CONFIG} clears the 5-PRB scheduler floor before any live run...",
          file=sys.stderr)
    if not verify_config_clears_floor(LIVE_CONFIG):
        print("[m49b2] ABORT: config does not clear the floor, per standing constraint", file=sys.stderr)
        return 1
    print("[m49b2] config verified clear. Proceeding with the live run.", file=sys.stderr)

    result = run_native_m8_style(EVAL_SEED)

    print(f"[m49b2] run result: error={result.get('error')} elapsed_s={result.get('elapsed_s')}",
          file=sys.stderr)
    if result.get("error") is not None:
        return 1

    ts2 = result["ts2"]
    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    m41dbg = m44e2b.parse_m41dbg(gnb_log, 0)

    # M41DBG e2_apply gives the commanded ceiling write; postpf gives the
    # scheduler's own post-write max_prbs read -- confirms whether accepted
    # requests actually clear the 5-PRB floor (the pre-fix run could not).
    sid_name = {1: "embb", 2: "mmtc", 3: "urllc"}
    for sid, name in sid_name.items():
        ceil_rows = [r for r in m41dbg["ceiling_rows"] if r["sid"] == sid]
        if not ceil_rows:
            print(f"[m49b2] {name}: no M41DBG ceiling rows found", file=sys.stderr)
            continue
        max_prbs_vals = [r["max_prbs"] for r in ceil_rows]
        below_floor_n = sum(1 for v in max_prbs_vals if v < 5)
        print(f"[m49b2] {name}: n_samples={len(max_prbs_vals)} "
              f"mean_max_prbs={sum(max_prbs_vals)/len(max_prbs_vals):.2f} "
              f"below_floor_n={below_floor_n} (0 expected post-fix)", file=sys.stderr)

    print(f"[m49b2] omega log: {RIG}/experiments/results/m49b_2/", file=sys.stderr)
    print(f"[m49b2] raw gNB log (for block-pattern + SLA-margin analysis): {gnb_log}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
