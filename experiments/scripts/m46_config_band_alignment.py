#!/usr/bin/env python3
"""M46-MR1: static band-alignment verification for the new M46 training
config. NO RIG -- pure static audit, reusing m42_floor_matrix.py's own
raw_prbs()/parse_slices() helpers (same conversion, same constants,
already verified against gNB_scheduler_dlsch.c in M41/M42) rather than
re-deriving the arithmetic by hand.

For each slice in experiments/configs/m46/saclb_m46_train.yaml, computes
floor/nominal/cap raw PRBs, enumerates every integer ratio point in
[floor, cap] to find the DISTINCT raw-PRB values that ratio range can
actually express (robust to any rounding-skip in the ratio->PRB mapping,
not just assumed from the endpoints), and checks whether the full
expressible set stays inside that slice's own live-measured graded band.

Bands are hardcoded from already-committed, already-measured milestone
results (not re-measured or invented here):
  urllc: 6-8 raw PRB  (M44-D, commit d3a9d12)
  embb:  5-10 raw PRB (M44-E2b, commit 4fb98dc)
  mmtc:  no band exists (M44-E1/E1b, commits 1e8d2b8/074b6ec) -- by this
         milestone's own design, mmtc's range is collapsed to one fixed
         point, not graded, so "in-band" does not apply to it in the
         usual sense; verified instead as fixed-and-at-scheduler-minimum.
"""
import csv
import sys
from pathlib import Path

RIG = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m42_floor_matrix import raw_prbs, parse_slices, N_RB_SCHED_INIT, MIN_RBSIZE  # noqa: E402

CONFIG_PATH = RIG / "experiments/configs/m46/saclb_m46_train.yaml"
OUT_DIR = RIG / "experiments/results/m46_mr1"

# (band_lo, band_hi) in raw PRBs, or None for "no band -- fixed by design"
TARGET_BANDS = {
    "urllc": (6, 8),
    "embb": (5, 10),
    "mmtc": None,
}
BAND_SOURCE = {
    "urllc": "M44-D (commit d3a9d12): 6,7,8 raw PRB @ 3600 Kbps (12x native)",
    "embb": "M44-E2b (commit 4fb98dc): 5,6,7,8,9,10 raw PRB @ 12000 Kbps (3x native)",
    "mmtc": "M44-E1/E1b (commits 1e8d2b8/074b6ec): no realistic band at any controllable+realistic load",
}


def expressible_raw_values(floor_ratio: int, cap_ratio: int) -> set:
    """Every distinct raw_prbs value reachable by an integer ratio in
    [floor_ratio, cap_ratio] -- enumerated, not assumed linear, so any
    rounding skip in raw_prbs() would still be caught."""
    return {raw_prbs(r) for r in range(floor_ratio, cap_ratio + 1)}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = CONFIG_PATH.read_text()
    slice_rows = parse_slices(text)
    assert slice_rows, f"no slices parsed from {CONFIG_PATH} -- parser/format mismatch, stop"

    rows = []
    verdicts = {}
    for slice_id, nominal, floor, cap in slice_rows:
        nominal_raw = raw_prbs(nominal)
        floor_raw = raw_prbs(floor)
        cap_raw = raw_prbs(cap)
        expressible = expressible_raw_values(floor, cap)
        band = TARGET_BANDS.get(slice_id)

        if band is None:
            # mmtc-style fixed slice: verify it's genuinely collapsed to
            # one point, and that point is not below the scheduler floor.
            is_fixed = (floor == nominal == cap)
            in_band = "N/A (fixed by design, no band exists)"
            note = (
                f"fixed-at-{floor_raw}raw" if is_fixed else
                "ERROR: expected floor==nominal==cap for a no-band slice, but they differ"
            )
            if not is_fixed:
                note = "ERROR: " + note
            elif floor_raw < MIN_RBSIZE:
                note += " -- ERROR: fixed value is BELOW min_rbSize, this slice would starve"
            distinct_count = len(expressible)
        else:
            band_lo, band_hi = band
            in_band = all(band_lo <= v <= band_hi for v in expressible) and floor_raw >= MIN_RBSIZE
            distinct_count = len(expressible)
            note = f"expressible raw PRBs: {sorted(expressible)}"

        rows.append({
            "slice": slice_id,
            "floor_ratio_pct": floor,
            "nominal_ratio_pct": nominal,
            "cap_ratio_pct": cap,
            "floor_raw_prbs": floor_raw,
            "nominal_raw_prbs": nominal_raw,
            "cap_raw_prbs": cap_raw,
            "min_rbSize": MIN_RBSIZE,
            "n_rb_sched_init": N_RB_SCHED_INIT,
            "target_band": f"{band[0]}-{band[1]}" if band else "N/A (no band, fixed by design)",
            "band_source": BAND_SOURCE[slice_id],
            "in_band": in_band,
            "distinct_points_expressible": distinct_count,
            "note": note,
        })
        verdicts[slice_id] = in_band

    out_csv = OUT_DIR / "config_band_alignment.csv"
    fieldnames = ["slice", "floor_ratio_pct", "nominal_ratio_pct", "cap_ratio_pct",
                  "floor_raw_prbs", "nominal_raw_prbs", "cap_raw_prbs", "min_rbSize",
                  "n_rb_sched_init", "target_band", "band_source", "in_band",
                  "distinct_points_expressible", "note"]
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[m46-mr1] wrote {len(rows)} rows to {out_csv}")
    for r in rows:
        print(f"  {r['slice']:6s} ratio[{r['floor_ratio_pct']},{r['nominal_ratio_pct']},{r['cap_ratio_pct']}] "
              f"-> raw[{r['floor_raw_prbs']},{r['nominal_raw_prbs']},{r['cap_raw_prbs']}] "
              f"target={r['target_band']:>10s} in_band={r['in_band']} "
              f"distinct_points={r['distinct_points_expressible']}")

    controllable = ["urllc", "embb"]
    all_in_band = all(verdicts[s] is True for s in controllable)
    all_multipoint = all(
        r["distinct_points_expressible"] > 1 for r in rows if r["slice"] in controllable
    )
    print()
    if all_in_band and all_multipoint:
        print("[m46-mr1] GATE MR1 VERDICT: config confound resolved statically -- "
              "both urllc and embb ranges are fully in-band and multi-point-graded. "
              "Proceed to MR2.")
    else:
        print("[m46-mr1] GATE MR1 VERDICT: STOP -- at least one controllable slice's "
              "range is NOT fully in-band or NOT graded-expressible. This reshapes "
              "the campaign; do not proceed to MR2 without review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
