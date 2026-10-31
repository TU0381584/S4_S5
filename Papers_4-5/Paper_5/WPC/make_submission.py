#!/usr/bin/env python3
"""Build the Wireless Personal Communications submission package from main.tex and supplementary.tex.

The journal asks for figure files named Fig1, Fig2, ... (EPS preferred), figures no wider than 119 mm,
and supplementary files named ESM_1.pdf and so on. This script
  1. numbers the main paper's figures in the order they appear,
  2. turns every inline TikZ figure into a standalone FigN.tex, compiled to FigN.pdf,
  3. copies every included graphic to FigN.pdf, and writes an EPS copy of each figure,
  4. writes submission/main.tex, which includes FigN.pdf at its natural size, never wider than 119 mm,
  5. copies refs.bib, the class and style files and Online Resource 1 as ESM_1.pdf, and compiles the package.
Run it from this directory after main.pdf and supplementary.pdf are up to date.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "submission")
MAX_W_PT = 119.0 / 25.4 * 72.27          # 119 mm in TeX points
MAX_W_BP = 119.0 / 25.4 * 72.0           # 119 mm in PDF points


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    return r


def labels_from_aux(aux):
    out = {}
    for m in re.finditer(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", open(aux).read()):
        out[m.group(1)] = m.group(2)
    return out


def tikz_preamble(main):
    """Packages, fonts, colours and icon macros that the inline TikZ figures rely on."""
    pre = main[:main.index("\\begin{document}")]
    macros = pre[pre.index("% --- reusable vector icons"):pre.index("\\newcommand{\\authorTODO}")]
    return ("\\documentclass[border=0pt]{standalone}\n\\usepackage{amsmath,amssymb}\n\\usepackage{xcolor}\n\\usepackage{tikz}\n"
            "\\renewcommand{\\sfdefault}{phv}\n"
            "\\usetikzlibrary{arrows.meta,fit,shapes.symbols,shapes.geometric,positioning,calc}\n" + macros)


def pdf_width_bp(pdf):
    info = run(["pdfinfo", pdf], HERE).stdout
    m = re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    return float(m.group(1)), float(m.group(2))


def main():
    main_tex = open(os.path.join(HERE, "main.tex")).read()
    labels = labels_from_aux(os.path.join(HERE, "main.aux"))
    os.makedirs(OUT, exist_ok=True)
    pre = tikz_preamble(main_tex)

    body_start = main_tex.index("\\begin{document}")
    figs = list(re.finditer(r"\\begin\{figure\}(\[[^\]]*\])?(.*?)\\end\{figure\}", main_tex[body_start:], re.S))
    new_tex = main_tex
    report = []
    for n, m in enumerate(figs, 1):
        opt, inner = m.group(1) or "", m.group(2)
        cap = inner[inner.index("\\caption{"):]
        name = f"Fig{n}"
        if "\\begin{tikzpicture}" in inner:
            body = inner[:inner.index("\\caption{")].replace("\\centering", "")
            body = re.sub(r"\\eqref\{([^}]+)\}", lambda k: f"({labels[k.group(1)]})", body)
            body = re.sub(r"\\ref\{([^}]+)\}", lambda k: labels[k.group(1)], body)
            open(os.path.join(OUT, name + ".tex"), "w").write(pre + "\\begin{document}\n" + body.strip() + "\n\\end{document}\n")
            run(["pdflatex", "-interaction=nonstopmode", name + ".tex"], OUT)
            for ext in (".aux", ".log"):
                if os.path.exists(os.path.join(OUT, name + ext)):
                    os.remove(os.path.join(OUT, name + ext))
            src = "TikZ"
        else:
            g = re.search(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", inner)
            path = os.path.join(HERE, g.group(2))
            if not path.endswith(".pdf"):
                path += ".pdf"
            shutil.copy(path, os.path.join(OUT, name + ".pdf"))
            src = os.path.basename(path)
        w, h = pdf_width_bp(os.path.join(OUT, name + ".pdf"))
        run(["pdftops", "-eps", name + ".pdf", name + ".eps"], OUT)
        width = "" if w <= MAX_W_BP + 0.5 else "[width=119mm]"
        new_fig = f"\\begin{{figure}}{opt}\n\\centering\n\\includegraphics{width}{{{name}}}\n{cap}\\end{{figure}}"
        new_tex = new_tex.replace(m.group(0), new_fig, 1)
        report.append((name, src, round(w / 72 * 25.4, 1), round(h / 72 * 25.4, 1), "scaled to 119 mm" if width else "natural size"))

    # figures now load from the package root; Online Resource 1 is supplied as ESM_1.pdf
    new_tex = new_tex.replace("\\graphicspath{{figures/}}", "")
    open(os.path.join(OUT, "main.tex"), "w").write(new_tex)
    for f in ("refs.bib", "sn-jnl.cls", "sn-basic.bst"):
        shutil.copy(os.path.join(HERE, f), OUT)
    shutil.copy(os.path.join(HERE, "supplementary.pdf"), os.path.join(OUT, "ESM_1.pdf"))
    for cmd in (["pdflatex", "-interaction=nonstopmode", "main.tex"], ["bibtex", "main"],
                ["pdflatex", "-interaction=nonstopmode", "main.tex"], ["pdflatex", "-interaction=nonstopmode", "main.tex"]):
        run(cmd, OUT)
    for name, src, w, h, how in report:
        print(f"{name}: {src:38s} {w:6.1f} x {h:5.1f} mm, {how}")


if __name__ == "__main__":
    main()
