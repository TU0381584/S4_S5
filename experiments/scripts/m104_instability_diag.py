import gzip, json, os, statistics as st
R = "/home/kmanojp/oranslice_rig/experiments/results"
def load(p):
    f = gzip.open(p + ".gz", "rt") if os.path.exists(p + ".gz") else open(p)
    return [json.loads(l) for l in f]
def run(cell, arm, seed):
    rows = [r for r in load(f"{R}/{cell}/{arm}/seed{seed}/train/omega_log.jsonl") if not r["evidence"].get("rollup")]
    last = max(r["episode"] for r in rows)
    seq = [r["evidence"]["accepted_counts"]["mmtc"] >= 5 for r in rows if r["episode"] > last - 3]
    return sum(a != b for a, b in zip(seq, seq[1:])), sum(seq) / len(seq)
groups = {"gat (M96+M101)": [("m96/A_fresh/n37_hex", "axiom2", s) for s in range(8000, 8020)] + [("m101/A_n37_hex", "axiom2", s) for s in range(9960, 9980)],
          "mlp (M100+M101)": [("m100/A_n37_hex", "axiom2_mlp", s) for s in range(8000, 8020)] + [("m101/A_n37_hex", "axiom2_mlp", s) for s in range(9960, 9980)],
          "concat (M103)": [("m103/A_n37_hex/concat", "axiom2", s) for s in range(9980, 10000)],
          "mlp (M103)": [("m103/A_n37_hex/mlp", "axiom2", s) for s in range(9980, 10000)]}
out = {}
for g, runs in groups.items():
    res = {f"{c}:{s}": run(c, a, s) for c, a, s in runs}
    sw = [v[0] for v in res.values()]; acc = [v[1] for v in res.values()]
    print(f"{g:18s} n={len(sw)} switching={sum(x>0 for x in sw)} median_sw={st.median(sw)} accept_share={100*st.mean(acc):.0f}% runs>20%={sum(a>0.2 for a in acc)}")
    out[g] = res
json.dump(out, open(f"{R}/m104_instability_diag.json", "w"), indent=0)
for k in [f"m103/A_n37_hex/concat:{s}" for s in (9980, 9983, 9984, 9985, 9986)]:
    print(k, out["concat (M103)"][k])
