#!/usr/bin/env python3
"""Paper 5 prose style check for a line range of a .tex file: sentences of 8 to 45 words,
no bold or italics, no body brackets (acronym definitions and CIs exempt), no colons in prose.

Usage: paper5_style_check.py FILE FIRST_LINE LAST_LINE
"""
import re
import sys

lines = open(sys.argv[1]).read().split("\n")
lo, hi = int(sys.argv[2]), int(sys.argv[3])
for i in range(lo - 1, min(hi, len(lines))):
    L = lines[i]
    if not L.strip() or L.lstrip().startswith(("%", "\\begin", "\\end", "\\caption", "\\label", "\\includegraphics", "\\centering",
                                                "\\item", "\\node", "\\draw", "\\STATE", "\\IF", "\\ENDIF", "\\FOR", "\\ENDFOR", "\\REQUIRE")) or "&" in L:
        continue
    t = re.sub(r"\$[^$]*\$", "X", L)
    t = re.sub(r"\\(ref|cite|label|eqref)\{[^}]*\}", "X", t)
    t = t.replace("~", " ").replace("et al.", "et al").replace("Fig. ", "Fig ").replace("Eq. ", "Eq ")
    if re.search(r"\\textbf|\\emph|\\textit", t):
        print(i + 1, "has bold/italic")
    body = re.sub(r"\((?:[A-Z][A-Za-z0-9-]*s?|[A-Za-z]+ [A-Za-z]+)\)", "", t)
    body = re.sub(r"\[[^\]]*\]", "", body)
    if "(" in body or ")" in body:
        print(i + 1, "has bracket", body[max(0, body.find("(") - 40):body.find("(") + 20])
    if re.search(r"[a-z]: ", body):
        print(i + 1, "has colon")
    for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", t):
        w = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'.,%-]*", sent))
        if w and (w <= 7 or w > 45):
            print(i + 1, "len", w, sent[:90])
