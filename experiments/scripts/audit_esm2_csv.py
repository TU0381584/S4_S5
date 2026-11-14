#!/usr/bin/env python3
"""Figure audit, Phase 2.5: Online Resource 2, the rliable results formerly printed as OR1 Table S2, as a CSV file.

Every value is copied at full precision from experiments/results/m93/m93_summary.json (rliable 1.2.0, stratified
bootstrap 95% CIs over 10,000 resamples), which m66_verify recomputes from the logs. One row per setting and policy.
Run: python audit_esm2_csv.py   (writes Papers_4-5/Paper_5/WPC/ESM_2.csv)
"""
import csv
import json

SRC = "/home/kmanojp/oranslice_rig/experiments/results/m93/m93_summary.json"
OUT = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/ESM_2.csv"
COLS = ["setting", "policy", "runs",
        "iqm_reward_per_gnb_per_step", "iqm_reward_ci95_low", "iqm_reward_ci95_high",
        "iqm_priority_slice_compliance_pct", "iqm_compliance_ci95_low", "iqm_compliance_ci95_high",
        "p_axiom_better_reward", "p_reward_ci95_low", "p_reward_ci95_high",
        "p_axiom_better_compliance", "p_compliance_ci95_low", "p_compliance_ci95_high"]
# Springer asks every supplementary file to name the article, journal, authors and corresponding author (2026-11-14);
# '#' lines without commas, so spreadsheet tools show each in one cell and pandas reads it with comment="#"
HEADER = ["# Online Resource 2",
          "# Article: AXIOM: A Shared Controller for Scalable Multi-Agent 5G Slice Admission",
          "# Journal: Wireless Personal Communications",
          "# Authors: Manoj Prasad Kunasegran; Wai Leong Pang; Swee King Phang",
          "# Corresponding author: Wai Leong Pang; waileong.pang@taylors.edu.my; School of Engineering; Faculty of "
          "Innovation and Technology; Taylor's University; 47500 Subang Jaya; Selangor; Malaysia",
          "# Content: rliable interquartile means (IQM) of reward per gNB per step and of priority-slice compliance (%) "
          "and the probability that AXIOM improves on each baseline; 95% stratified bootstrap CIs over 10000 resamples; "
          "one row per setting and policy; empty cells for AXIOM against itself"]


def rows():
    s = json.load(open(SRC))
    for name, st in s["settings"].items():
        for pol, p in st["policies"].items():
            r = [name, pol, p["runs"], p["iqm_reward"], *p["iqm_reward_ci"], p["iqm_prio"], *p["iqm_prio_ci"]]
            if pol == "AXIOM":
                r += [""] * 6
            else:
                r += [p["poi_reward"], *p["poi_reward_ci"], p["poi_prio"], *p["poi_prio_ci"]]
            yield [repr(x) if isinstance(x, float) else x for x in r]


if __name__ == "__main__":
    assert all("," not in h for h in HEADER)
    with open(OUT, "w", newline="") as f:
        f.write("\r\n".join(HEADER) + "\r\n")   # csv.writer ends rows with CRLF too
        w = csv.writer(f)
        w.writerow(COLS)
        n = 0
        for r in rows():
            w.writerow(r); n += 1
    print(f"{OUT}: {n} rows")
