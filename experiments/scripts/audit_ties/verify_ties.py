"""Manuscript verifier with Wilcoxon ties recognised (differences rounded to 1e-9). Run from framework/: ../venv/bin/python ../experiments/scripts/audit_ties/verify_ties.py <outdir>"""
import sys, numpy as np
OUT = sys.argv[1]   # output directory
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
import m66_verify as V
from scipy.stats import wilcoxon as W
changed = []
def w(x, y=None, **kw):
    a = W(x, y, **kw)
    xr = np.round(np.asarray(x, float) - (0 if y is None else np.asarray(y, float)), 9)
    b = W(xr, **kw)
    if abs(a.pvalue - b.pvalue) > 1e-12:
        changed.append((a.pvalue, b.pvalue, len(xr), int((xr != 0).sum()), len(set(np.abs(xr[xr != 0]))), int((np.asarray(x, float) - (0 if y is None else np.asarray(y, float)) != 0).sum())))
    return b
V.wilcoxon = w
sys.argv = ["m66_verify", "--tex", "../Papers_4-5/Paper_5/WPC/main.tex", "--supp", "../Papers_4-5/Paper_5/WPC/supplementary.tex",
            "--out", OUT + "/verify_ties.json"]
V.main()
print("tests whose p changes when ties are recognised:", len(changed))
print("crossing 0.05:", [c for c in changed if (c[0] < 0.05) != (c[1] < 0.05)])
import json; json.dump(changed, open(OUT + "/tie_changes.json", "w")); [print(c) for c in sorted(changed, key=lambda c: -abs(c[0]-c[1])/c[0])]
