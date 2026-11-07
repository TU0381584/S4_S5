#!/usr/bin/env python3
"""contact_sheet.pdf: each variant at true print size (vector PDF, 130.7 mm wide), with its greyscale and deuteranopia
previews beside it at the same size. One variant per page. Built with pdflatex. Run: python make_contact_sheet.py
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
V = [("A", "fig10_A", "Option A: dot-plot strips and capability table"),
     ("B", "fig10_B", "Option B: trade-off scatter"),
     ("C", "fig10_C", "Option C: annotated normalised heatmap"),
     ("D", "fig10_D", "Option D: radar chart, default axis order"),
     ("D_alt", "fig10_D_alt", "Option D: radar chart, permuted axis order")]


def main():
    W = 130.7
    body = []
    for _, stem, title in V:
        body.append(rf"""\noindent{{\large {title}}}\hfill true print size, width {W} mm\par\medskip
\noindent\begin{{tabular}}{{@{{}}c@{{\hspace{{8mm}}}}c@{{\hspace{{8mm}}}}c@{{}}}}
\includegraphics[width={W}mm]{{{stem}.pdf}} & \includegraphics[width={W}mm]{{{stem}_grey.png}} & \includegraphics[width={W}mm]{{{stem}_cvd.png}}\\[2mm]
Colour (vector PDF) & Greyscale, CIE $L^*$ & Deuteranopia simulation (colorspacious, severity 100)
\end{{tabular}}
\newpage""")
    tex = rf"""\documentclass{{article}}
\usepackage[paperwidth=440mm,paperheight=150mm,margin=10mm]{{geometry}}
\usepackage{{graphicx}}
\usepackage[scaled]{{helvet}}\renewcommand{{\familydefault}}{{\sfdefault}}
\pagestyle{{empty}}
\begin{{document}}
{chr(10).join(body)}
\end{{document}}
"""
    open(os.path.join(HERE, "contact_sheet.tex"), "w").write(tex)
    for _ in range(1):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "contact_sheet.tex"], cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    for ext in (".aux", ".log"):
        p = os.path.join(HERE, "contact_sheet" + ext)
        if os.path.exists(p):
            os.remove(p)
    print("contact_sheet.pdf written")


if __name__ == "__main__":
    main()
