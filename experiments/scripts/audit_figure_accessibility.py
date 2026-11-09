#!/usr/bin/env python3
"""Colour-vision and greyscale audit of every figure in the WPC submission (2026-11-10).

Springer Nature's artwork guidelines for Wireless Personal Communications ask that the main information stays
visible when a colour figure is converted to black and white, and that captions do not refer to colour. This audit:
  1. renders every main figure as submitted (submission/Fig1.pdf to FigN.pdf) and every Online Resource 1 figure
     (its PDF, or its page of ESM_1.pdf for inline TikZ) at 300 dpi;
  2. writes a greyscale (CIE L*) version and deuteranomaly, protanomaly and tritanomaly simulations (severity 100)
     of each, and contact sheets of all five versions, for inspection by eye;
  3. lists, for every pair of policy colours, the CAM02-UCS distance in colour and under each CVD simulation,
     the greyscale lightness difference, and whether the pair also differs in marker shape or fill;
  4. lists any colour word in a main or Online Resource 1 caption.
Run from the repo root: venv/bin/python experiments/scripts/audit_figure_accessibility.py --out <dir>
Writes <dir>/report.json and the previews; prints a summary.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

WPC = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC"
sys.path.insert(0, f"{WPC}/figures")
import axiom_style as S  # noqa: E402


def render(pdf, out_png, page=None):
    args = ["pdftoppm", "-png", "-r", "300", "-singlefile"]
    if page:
        args += ["-f", str(page), "-l", str(page)]
    subprocess.run(args + [pdf, out_png[:-4]], check=True)
    return out_png


def captions(tex):
    s = open(tex).read()
    return re.findall(r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}", s)


def sheet(pngs, out, width=900):
    ims = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        ims.append(im.resize((width, int(im.height * width / im.width))))
    cols = 2
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    H = sum(max(i.height for i in r) for r in rows)
    canvas = Image.new("RGB", (width * cols, H), "white")
    y = 0
    for r in rows:
        for k, im in enumerate(r):
            canvas.paste(im, (k * width, y))
        y += max(i.height for i in r)
    canvas.save(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    figs = {}
    for pdf in sorted(glob.glob(f"{WPC}/submission/Fig*.pdf"), key=lambda p: int(re.findall(r"\d+", os.path.basename(p))[0])):
        name = os.path.basename(pdf)[:-4]
        figs[name] = render(pdf, f"{a.out}/{name}.png")
    sup = open(f"{WPC}/supplementary.tex").read()
    for k, f in enumerate(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", sup), 1):
        figs[f"OR1_{os.path.basename(f)[:-4]}"] = render(f"{WPC}/{f}", f"{a.out}/OR1_{os.path.basename(f)[:-4]}.png")
    # inline TikZ figures of OR1: render their page of ESM_1.pdf
    n_pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", f"{WPC}/submission/ESM_1.pdf"], capture_output=True, text=True).stdout).group(1))
    for p in range(1, n_pages + 1):
        t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), f"{WPC}/submission/ESM_1.pdf", "-"], capture_output=True, text=True).stdout
        if re.search(r"^Fig\. S\d+ .*(testbed|Testbed)", t, re.M):
            figs[f"OR1_page{p}"] = render(f"{WPC}/submission/ESM_1.pdf", f"{a.out}/OR1_page{p}.png", page=p)
    for name, png in figs.items():
        S.cvd_previews(png)
    prev = os.path.join(a.out, "audit_previews")
    for group, keys in (("main", [k for k in figs if k.startswith("Fig")]), ("or1", [k for k in figs if k.startswith("OR1")])):
        for tag in ("", "_grey", "_deut", "_prot", "_trit"):
            sheet([figs[k] if not tag else f"{prev}/{k}{tag}.png" for k in keys], f"{a.out}/sheet_{group}{tag or '_colour'}.png")
    pols = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static", "rule_local", "rule_neighbour", "rule_accept_all"]
    sep = S.token_separation(pols)
    caps = {"main": captions(f"{WPC}/main.tex"), "or1": captions(f"{WPC}/supplementary.tex")}
    words = {d: [(i + 1, S.caption_colour_words(c)) for i, c in enumerate(cs) if S.caption_colour_words(c)] for d, cs in caps.items()}
    rep = {"figures": list(figs), "token_separation": {f"{k[0]}|{k[1]}" if isinstance(k, tuple) else k: v for k, v in sep.items()},
           "caption_colour_words": words}
    json.dump(rep, open(f"{a.out}/report.json", "w"), indent=1, default=float)
    print(len(figs), "figures rendered:", ", ".join(figs))
    worst = []
    for k, v in rep["token_separation"].items():
        cvd = min(v[t] for t in ("deuteranomaly", "protanomaly", "tritanomaly"))
        worst.append((cvd, v["grey_dL"], v["shape_differs"], k))
    print("policy pairs, min CVD dE, grey dL, shape differs:")
    for w in sorted(worst):
        print(f"  {w[3]:40s} {w[0]:6.1f} {w[1]:6.1f} {w[2]}")
    print("caption colour words:", words)


if __name__ == "__main__":
    main()
