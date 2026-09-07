#!/usr/bin/env python3
"""M45-PF1: the priority-weighted cross-slice correctness metric.

Judges urllc+embb co-located runs from real radio state -- served-vs-
offered throughput (corrected parser, handles bare-"0.00" zero-rate
lines) and RLC AM SDU-reject fraction (M43DBG instrumentation) -- NOT
sla_compliance_all_slices (P0-blind to complete starvation by
construction: dl_errors=0/dl_bler=0 for a slice receiving zero grants),
and not derived from either DQN reward's own machinery (compute_qoe_reward's
sla_viol term shares check_violations' exact blind spot, so a judge
built from it would not be independent of what it's judging).

W_URLLC/W_EMBB are not invented: they are priority_weight (omega_k in
papers #1/#2's eq.2) read directly from the submitted, frozen
experiments/configs/saclb_campaign_v2.yaml (urllc=5.0, embb=3.5 -- the
two highest of the three configured slices, mmtc=0.3 excluded here
since mmtc has no realistic band per M44-E1b).

See docs/PAPER5_M45_PF1_priority_weighted_correctness.md for the full
spec and sensitivity argument. This script implements the metric only;
it does not run anything live.
"""
import json
import sys
from pathlib import Path

RIG = Path(__file__).resolve().parents[2]

# priority_weight (omega_k) from experiments/configs/saclb_campaign_v2.yaml,
# NOT re-derived here -- cite that file, don't hardcode-and-forget.
W_URLLC = 5.0
W_EMBB = 3.5


def clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_c_k(served_kbps: float | None, offered_kbps: float, rlc_rej_pct: float | None) -> float | None:
    """C_k(t) = clip(served/offered, 0, 1) * (1 - rlc_reject_frac).
    Returns None if either input is missing this window (don't invent a
    number for a window with no data -- exclude it from the mean instead
    of silently imputing)."""
    if served_kbps is None or offered_kbps in (None, 0) or rlc_rej_pct is None:
        return None
    throughput_frac = clip01(served_kbps / offered_kbps)
    reject_frac = clip01(rlc_rej_pct / 100.0)
    return throughput_frac * (1.0 - reject_frac)


def compute_score(c_urllc: float | None, c_embb: float | None) -> float | None:
    """Score(t) = (w_urllc*C_urllc + w_embb*C_embb) / (w_urllc + w_embb)."""
    if c_urllc is None or c_embb is None:
        return None
    return (W_URLLC * c_urllc + W_EMBB * c_embb) / (W_URLLC + W_EMBB)


def compute_pwc_for_trajectory(rows: list[dict]) -> dict:
    """rows: the per-sample dicts already written by M44-D/E1b/E2b/E4-style
    scripts, expecting urllc_served_kbps/urllc_offered_kbps/urllc_rlc_rej_pct
    and embb_served_kbps/embb_offered_kbps/embb_rlc_rej_pct keys (E4's own
    trajectory schema). Uses the last 4 of however many samples are present,
    matching this project's own established steady-state-window convention."""
    last4 = rows[-4:] if len(rows) >= 4 else rows
    c_urllc_list, c_embb_list, score_list = [], [], []
    for r in last4:
        c_u = compute_c_k(r.get("urllc_served_kbps"), r.get("urllc_offered_kbps"), r.get("urllc_rlc_rej_pct"))
        c_e = compute_c_k(r.get("embb_served_kbps"), r.get("embb_offered_kbps"), r.get("embb_rlc_rej_pct"))
        c_urllc_list.append(c_u)
        c_embb_list.append(c_e)
        s = compute_score(c_u, c_e)
        score_list.append(s)

    valid_u = [x for x in c_urllc_list if x is not None]
    valid_e = [x for x in c_embb_list if x is not None]
    valid_s = [x for x in score_list if x is not None]
    return {
        "n_windows_used": len(last4),
        "n_windows_valid": len(valid_s),
        "mean_c_urllc": sum(valid_u) / len(valid_u) if valid_u else None,
        "mean_c_embb": sum(valid_e) / len(valid_e) if valid_e else None,
        "pwc": sum(valid_s) / len(valid_s) if valid_s else None,
        "per_window_c_urllc": c_urllc_list,
        "per_window_c_embb": c_embb_list,
        "per_window_score": score_list,
    }


def main() -> int:
    """Validation mode: apply PWC to M44-E4's own already-collected
    trajectory files (no rig time -- these are already on disk)."""
    e4_dir = RIG / "experiments/results/m44e4"
    combos = [(6, 7), (7, 7), (8, 7), (7, 5), (7, 8), (7, 10)]
    out_path = RIG / "experiments/results/m45_preflight/pf1_validation.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with out_path.open("w") as out_f:
        for uc, ec in combos:
            traj_path = e4_dir / f"trajectory_u{uc}e{ec}.jsonl"
            if not traj_path.exists():
                print(f"[pf1] WARNING: {traj_path} not found, skipping", file=sys.stderr)
                continue
            rows = [json.loads(l) for l in traj_path.read_text().splitlines() if l.strip()]
            pwc_result = compute_pwc_for_trajectory(rows)
            row = {"urllc_ceil": uc, "embb_ceil": ec, **pwc_result}
            results.append(row)
            out_f.write(json.dumps(row) + "\n")
            print(f"[pf1] urllc_ceil={uc} embb_ceil={ec}  mean_C_urllc={pwc_result['mean_c_urllc']:.3f} "
                  f"mean_C_embb={pwc_result['mean_c_embb']:.3f}  PWC={pwc_result['pwc']:.3f}",
                  file=sys.stderr)

    print(f"\n[pf1] === validation table (also written to {out_path}) ===", file=sys.stderr)
    print(f"{'urllc':>6} {'embb':>6} {'C_urllc':>9} {'C_embb':>8} {'PWC':>7}", file=sys.stderr)
    for r in results:
        print(f"{r['urllc_ceil']:>6} {r['embb_ceil']:>6} {r['mean_c_urllc']:>9.3f} "
              f"{r['mean_c_embb']:>8.3f} {r['pwc']:>7.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
