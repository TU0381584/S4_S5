#!/usr/bin/env python3
"""Coverage check (2026-11-10): is every number in the abstract, discussion and conclusion inside text that the
verifier (m66_verify.py) or the M82 audit (m82_audit.py) matches against the manuscript?

Every string the two scripts can look for is rebuilt from their source with Python's ast module: plain string
constants are matched verbatim, and f-strings and str.format templates become patterns whose computed parts match
any short run of text. A number in a target section is covered when it lies inside a match. Uncovered numbers are
listed with their context for inspection by hand; this script judges nothing by itself.

Usage: venv/bin/python experiments/scripts/audit_check_coverage.py --tex Papers_4-5/Paper_5/WPC/main.tex --out <json>
"""
import argparse
import ast
import json
import re

SCRIPTS = ["/home/kmanojp/oranslice_rig/experiments/scripts/m66_verify.py", "/home/kmanojp/oranslice_rig/experiments/scripts/m82_audit.py"]
SLOT = r"[^&\n]{1,40}?"


def patterns(src):
    tree = ast.parse(src)
    lits, regs = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 6:
            v = node.value
            lits.add(v)
            if re.search(r"\{[A-Za-z_0-9:.,<>+]*\}", v):   # a str.format template
                parts = re.split(r"\{[A-Za-z_0-9:.,<>+]*\}", v)
                if sum(len(p) for p in parts) >= 6:
                    regs.add(SLOT.join(re.escape(p) for p in parts))
        elif isinstance(node, ast.JoinedStr):
            out, const = [], 0
            for v in node.values:
                if isinstance(v, ast.Constant):
                    out.append(re.escape(v.value)); const += len(v.value)
                else:
                    out.append(SLOT)
            if const >= 6:
                regs.add("".join(out))
    return lits, regs


def sections(tex, every=False):
    s = {}
    if every:   # every numbered section of the body, from Introduction to the Conclusion
        heads = [m for m in re.finditer(r"\\section\*?\{([^}]*)\}", tex)]
        for k, m in enumerate(heads):
            end = heads[k + 1].start() if k + 1 < len(heads) else (tex.find("\\backmatter") if "\\backmatter" in tex else len(tex))
            s[m.group(1)] = (m.start(), end)
    m = re.search(r"\\abstract\{(.*?)\}\n", tex, re.S)
    if m:
        s["abstract"] = (m.start(1), m.end(1))
    for name in ("Discussion and Limitations", "Conclusion"):
        i = tex.find(f"\\section{{{name}}}")
        if i >= 0:
            j = tex.find("\\section", i + 10)
            s[name] = (i, j if j > 0 else len(tex))
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tex", required=True); ap.add_argument("--out", required=True); ap.add_argument("--all", action="store_true"); a = ap.parse_args()
    tex = open(a.tex).read()
    lits, regs = set(), set()
    for f in SCRIPTS:
        l_, r_ = patterns(open(f).read()); lits |= l_; regs |= r_
    covered = bytearray(len(tex))
    for s in lits:
        i = tex.find(s)
        while i >= 0:
            covered[i:i + len(s)] = b"\x01" * len(s)
            i = tex.find(s, i + 1)
    for r in regs:
        try:
            for m in re.finditer(r, tex):
                covered[m.start():m.end()] = b"\x01" * (m.end() - m.start())
        except re.error:
            pass
    rep = {}
    for name, (lo, hi) in sections(tex, a.all).items():
        nums = [m for m in re.finditer(r"(?<![\w\\{])\d+(?:[.,{}]+\d+)*(?:\\%)?", tex[lo:hi])]
        unc = []
        for m in nums:
            st, en = lo + m.start(), lo + m.end()
            ctx = tex[max(lo, st - 70):min(hi, en + 40)].replace("\n", " ")
            if re.search(r"\\(ref|cite|label)\{[^}]*$", tex[max(0, st - 40):st]):
                continue
            if not all(covered[st:en]):
                unc.append({"number": m.group(0), "context": ctx})
        rep[name] = {"numbers": len(nums), "uncovered": unc}
        print(f"{name}: {len(nums)} numbers, {len(unc)} not inside checked text")
        if not a.all:
            for u in unc:
                print(f"   {u['number']:>10s} | {u['context']}")
    json.dump(rep, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
