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


# M45-PF1b addition 1: equal-weight variant (w=1/1), reported alongside the
# priority-weighted PWC for every arm. See PAPER5_M45_PF1_... doc section on
# "weighting-bias robustness": PWC's 5.0/3.5 weights come from DQN-SLA's own
# eq.2 objective, so a reviewer could dismiss an SLA win as metric bias. If
# PWC and PWC_eq rank the same arms the same way, the result is robust to the
# weighting choice; if the ranking flips, the flip itself isolates what
# priority-weighting specifically buys (see the doc for the full argument).
def compute_equal_weight_score(c_urllc: float | None, c_embb: float | None) -> float | None:
    if c_urllc is None or c_embb is None:
        return None
    return (c_urllc + c_embb) / 2.0


# M45-PF1b addition 2: correct-shedding classification. C_k alone cannot
# distinguish "embb correctly shed to protect urllc" (reward-optimal) from
# "embb dropped and urllc failed anyway" (indiscriminate failure) -- both
# read as a low C_embb. Thresholds are read off this project's own already-
# measured data, not invented:
#   TAU_PROTECT_URLLC=0.75 sits in the clear bimodal gap in E4's own
#   per-window C_urllc values (a degraded cluster at 0.37-0.48, a healthy
#   cluster at 0.63-0.91 -- see pf1b_validation.jsonl).
#   TAU_SHED_EMBB=0.5 sits above the ENTIRE measured embb graded-band range
#   from M44-E2b's own solo characterization (C_embb 0.10-0.375 across all
#   6 of embb's own solo ceilings under the same 3x-native stress load) and
#   above every embb C value observed in E4's co-located data (max 0.237) --
#   i.e. embb reading below 0.5 means "in the band this rig already
#   established as embb's real degraded operating region," not an arbitrary
#   split.
TAU_PROTECT_URLLC = 0.75
TAU_SHED_EMBB = 0.5


def classify_window(c_urllc: float | None, c_embb: float | None) -> str | None:
    """One of:
    - "protected_no_shed_needed": urllc healthy, embb also not meaningfully shed.
    - "correct_shed": urllc healthy, embb was shed -- the reward-optimal tradeoff.
    - "indiscriminate_failure": urllc failed AND embb was shed -- the sacrifice bought nothing.
    - "priority_inversion": urllc failed while embb was NOT shed -- the worst case
      (headroom existed to shed embb and protect urllc; the system didn't take it).
    Returns None if data is missing this window."""
    if c_urllc is None or c_embb is None:
        return None
    urllc_protected = c_urllc >= TAU_PROTECT_URLLC
    embb_shed = c_embb < TAU_SHED_EMBB
    if urllc_protected and not embb_shed:
        return "protected_no_shed_needed"
    if urllc_protected and embb_shed:
        return "correct_shed"
    if (not urllc_protected) and embb_shed:
        return "indiscriminate_failure"
    return "priority_inversion"


def compute_shedding_metrics(per_window_c_urllc: list, per_window_c_embb: list) -> dict:
    """Shed-Precision = (correct sheds) / (all shed events), mirroring Paper
    #5 Sec.5's block-precision structure: among the windows where embb was
    actually shed, what fraction achieved their purpose (urllc protected)?
    Priority-Inversion-Rate = (priority inversions) / (all urllc-failure
    windows): among the windows where urllc failed, what fraction happened
    while embb was NOT even being shed (a wasted opportunity to protect
    urllc, not genuine resource exhaustion)? Both are None (not 0) when
    their own denominator is 0 -- an undefined rate is not the same as a
    perfect or zero one, and should not be reported as either."""
    classes = [classify_window(u, e) for u, e in zip(per_window_c_urllc, per_window_c_embb)]
    valid_classes = [c for c in classes if c is not None]

    n_shed_events = sum(1 for c in valid_classes if c in ("correct_shed", "indiscriminate_failure"))
    n_correct_shed = sum(1 for c in valid_classes if c == "correct_shed")
    n_urllc_failed = sum(1 for c in valid_classes if c in ("indiscriminate_failure", "priority_inversion"))
    n_priority_inversion = sum(1 for c in valid_classes if c == "priority_inversion")

    return {
        "window_classes": classes,
        "n_windows_valid": len(valid_classes),
        "n_shed_events": n_shed_events,
        "n_correct_shed": n_correct_shed,
        "shed_precision": (n_correct_shed / n_shed_events) if n_shed_events > 0 else None,
        "n_urllc_failed": n_urllc_failed,
        "n_priority_inversion": n_priority_inversion,
        "priority_inversion_rate": (n_priority_inversion / n_urllc_failed) if n_urllc_failed > 0 else None,
    }


def compute_pwc_for_trajectory(rows: list[dict]) -> dict:
    """rows: the per-sample dicts already written by M44-D/E1b/E2b/E4-style
    scripts, expecting urllc_served_kbps/urllc_offered_kbps/urllc_rlc_rej_pct
    and embb_served_kbps/embb_offered_kbps/embb_rlc_rej_pct keys (E4's own
    trajectory schema). Uses the last 4 of however many samples are present,
    matching this project's own established steady-state-window convention."""
    last4 = rows[-4:] if len(rows) >= 4 else rows
    c_urllc_list, c_embb_list, score_list, score_eq_list = [], [], [], []
    for r in last4:
        c_u = compute_c_k(r.get("urllc_served_kbps"), r.get("urllc_offered_kbps"), r.get("urllc_rlc_rej_pct"))
        c_e = compute_c_k(r.get("embb_served_kbps"), r.get("embb_offered_kbps"), r.get("embb_rlc_rej_pct"))
        c_urllc_list.append(c_u)
        c_embb_list.append(c_e)
        score_list.append(compute_score(c_u, c_e))
        score_eq_list.append(compute_equal_weight_score(c_u, c_e))

    valid_u = [x for x in c_urllc_list if x is not None]
    valid_e = [x for x in c_embb_list if x is not None]
    valid_s = [x for x in score_list if x is not None]
    valid_seq = [x for x in score_eq_list if x is not None]
    shedding = compute_shedding_metrics(c_urllc_list, c_embb_list)
    return {
        "n_windows_used": len(last4),
        "n_windows_valid": len(valid_s),
        "mean_c_urllc": sum(valid_u) / len(valid_u) if valid_u else None,
        "mean_c_embb": sum(valid_e) / len(valid_e) if valid_e else None,
        "pwc": sum(valid_s) / len(valid_s) if valid_s else None,
        "pwc_equal_weight": sum(valid_seq) / len(valid_seq) if valid_seq else None,
        "per_window_c_urllc": c_urllc_list,
        "per_window_c_embb": c_embb_list,
        "per_window_score": score_list,
        "per_window_score_equal_weight": score_eq_list,
        "shedding": shedding,
    }


def _fmt(x, prec=3):
    return f"{x:.{prec}f}" if x is not None else "N/A"


def main() -> int:
    """Validation mode: apply PWC (+PF1b's equal-weight and correct-shedding
    additions) to M44-E4's own already-collected trajectory files (no rig
    time -- these are already on disk)."""
    e4_dir = RIG / "experiments/results/m44e4"
    combos = [(6, 7), (7, 7), (8, 7), (7, 5), (7, 8), (7, 10)]
    out_path = RIG / "experiments/results/m45_preflight/pf1b_validation.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with out_path.open("w") as out_f:
        for uc, ec in combos:
            traj_path = e4_dir / f"trajectory_u{uc}e{ec}.jsonl"
            if not traj_path.exists():
                print(f"[pf1b] WARNING: {traj_path} not found, skipping", file=sys.stderr)
                continue
            rows = [json.loads(l) for l in traj_path.read_text().splitlines() if l.strip()]
            pwc_result = compute_pwc_for_trajectory(rows)
            row = {"urllc_ceil": uc, "embb_ceil": ec, **pwc_result}
            results.append(row)
            out_f.write(json.dumps(row) + "\n")
            sh = pwc_result["shedding"]
            print(f"[pf1b] u={uc} e={ec}  PWC={_fmt(pwc_result['pwc'])} "
                  f"PWC_eq={_fmt(pwc_result['pwc_equal_weight'])}  "
                  f"shed_precision={_fmt(sh['shed_precision'])} "
                  f"priority_inversion_rate={_fmt(sh['priority_inversion_rate'])} "
                  f"classes={sh['window_classes']}", file=sys.stderr)

    # weighting-bias check: does PWC's ranking match PWC_eq's ranking?
    ranked_pwc = sorted(results, key=lambda r: r["pwc"], reverse=True)
    ranked_eq = sorted(results, key=lambda r: r["pwc_equal_weight"], reverse=True)
    order_pwc = [(r["urllc_ceil"], r["embb_ceil"]) for r in ranked_pwc]
    order_eq = [(r["urllc_ceil"], r["embb_ceil"]) for r in ranked_eq]
    ranking_matches = order_pwc == order_eq

    print(f"\n[pf1b] === validation table (also written to {out_path}) ===", file=sys.stderr)
    print(f"{'urllc':>6} {'embb':>6} {'PWC':>7} {'PWC_eq':>7} {'shed_prec':>10} {'inv_rate':>9}",
          file=sys.stderr)
    for r in results:
        sh = r["shedding"]
        print(f"{r['urllc_ceil']:>6} {r['embb_ceil']:>6} {_fmt(r['pwc']):>7} "
              f"{_fmt(r['pwc_equal_weight']):>7} {_fmt(sh['shed_precision']):>10} "
              f"{_fmt(sh['priority_inversion_rate']):>9}", file=sys.stderr)
    print(f"\n[pf1b] ranking by PWC (weighted):     {order_pwc}", file=sys.stderr)
    print(f"[pf1b] ranking by PWC_eq (1/1):       {order_eq}", file=sys.stderr)
    print(f"[pf1b] rankings identical: {ranking_matches}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
