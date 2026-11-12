"""Lists verifier tests where a zero difference is stored as float noise (0 < |d| < 1e-9). Run from framework/: ../venv/bin/python ../experiments/scripts/audit_ties/verify_nearzero.py <outdir>"""
import sys, numpy as np, traceback
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
import m66_verify as V
orig = V.paired
hits = []
def paired(a, b, f=lambda r: r["reward"]):
    x = orig(a, b, f)
    common = sorted(set(a) & set(b))
    d = np.array([f(a[s]) - f(b[s]) for s in common])
    nz = d[(d != 0) & (np.abs(d) < 1e-9)]
    if len(nz):
        st = traceback.extract_stack()[-2]
        hits.append((st.filename.split("/")[-1] + ":" + str(st.lineno), len(d), x["wins"], x["ties"], x["losses"], len(nz), float(np.abs(nz).max())))
    return x
V.paired = paired
sys.argv = ["m66_verify", "--tex", "../Papers_4-5/Paper_5/WPC/main.tex", "--supp", "../Papers_4-5/Paper_5/WPC/supplementary.tex", "--out", f"{sys.argv[1]}/verify_nz.json"]
V.main()
print("tests with float-noise non-ties:", len(hits))
for h in sorted(set(hits)):
    print("verifier line", h[0], "n", h[1], "W/T/L", h[2:5], "noise entries", h[5], "max", h[6])
