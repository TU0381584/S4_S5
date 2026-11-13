# M107: seed extension of the Figs. 5 and 7 cells (results)

These are the results for docs/PAPER5_M107_preregistration.md, which was committed in 426a3281 before any run.

## Runs

The campaign ran from 2026-11-12 20:39 to 2026-11-13 23:25. All 1,005 of 1,005 jobs exited 0.

- All 990 learned runs trained for exactly 300 episodes.
- Every evaluation log has 50 episodes.
- Logs are kept gzip-compressed.

## Analysis

The pre-registered analysis is experiments/results/m107/analysis.json, produced by m107_analysis.py. On the stored seeds it reproduces every number the paper printed before pooling.

Deviation to report: m107_analysis.py groups each cell's tests into one Holm family, with reward and compliance together and every baseline in it. The pre-registration says "Holm within each family as in the paper". The paper's own families are smaller:
- The Table 3 family has 7 reward comparisons.
- The 37-gNB tests split into hex and non-hex families.

The manuscript uses the paper's own families, through m66_verify.py, because those are the families its text describes. analysis.json is kept unchanged as the pre-registered output.

## Verdicts that changed with pooling (paper families)

| Setting | Comparison | First 30 seeds | New seeds alone | Pooled |
|---|---|---|---|---|
| Env A, 3 gNBs | AXIOM vs DQN-SA, reward | +0.311, Holm p 0.066 | +0.312, p 0.051 | +0.312, p 0.0021, AXIOM ahead |
| Env A, 3 gNBs | AXIOM vs MLP encoder, reward | +0.058, p 0.088 | +0.079, p 0.18 | +0.068, p 0.015, AXIOM ahead (mean CI spans zero) |
| Env A, 3 gNBs | AXIOM vs static rule, reward | -0.138, p 0.16 | -0.064, p 0.18 | -0.101, p 0.040, rule ahead |
| Env B, 3 gNBs | AXIOM vs tuned neighbour rule, reward | -0.209, p 0.061 | -0.261 | -0.235, p 0.012, rule ahead |
| Env A, 19 gNBs, nominal load (Fig. 10a) | AXIOM vs static rule, compliance | -2.7, p 0.056 | | -2.5, p 0.0032, rule ahead |

## Not reproduced by the new seeds alone (pre-registration item 2)

Two leads were not reproduced:

- **Env A, 7 gNBs, ring layout, AXIOM vs DQN-SA, both measures.** On the 15 new seeds the analysis.json family gives Holm p 0.11. The new DQN-SA runs averaged 86.3% compliance, against 74.5% on the stored seeds; DQN-SA is unseeded there, as in M64 and M65. Pooled, the lead holds at p <= 0.0003.
- **Env B, 3 gNBs, AXIOM's compliance lead over the tuned neighbour rule.** It is p 0.15 on the new seeds alone and p 0.012 pooled.

Both are reported in the main paper's verification section.

## Infrastructure fixes found during switch-over

- **Subset reads.** The extension was keyed by the seed list alone. A read of a 19-gNB cell with the 15-seed subset, as in the M92 transfer section, would have added 15 new seeds. A sample is now extended only when it is read with that cell's full stored list (`_full_list` in m66_verify.py).
- **Stored-seed loops.** Four difference CIs in m66_verify.py, for the Table 3 paragraph, iterated the stored seed list; the probe had not flagged them. They now use every paired seed of the sample.

## Author decisions (2026-11-14)

- The manuscript, figures and tables move to the pooled seeds.
- The 30+10 replication paragraph keeps the first 30 seeds plus the 10 replication seeds.
- Campaigns that pair their own runs seed by seed with these cells keep their stored comparisons: M74, M75 C, M76 VDN, M92 transfer, the M70 MAPPO grid and the M63 reuse audit. This is done with `pin_stored` or `pool=False` in m66_verify.py.

## State after switch-over

- Verifier: 663/663 with --supp.
- CI recompute: 19 intervals in the main paper and 2 in OR1 match exactly.
- rliable: S2 has 0 mismatches, and all 51 orderings hold.
- Page counts: main 29 pp, OR1 10 pp, with no overfull boxes.
- The submission package has been rebuilt.
