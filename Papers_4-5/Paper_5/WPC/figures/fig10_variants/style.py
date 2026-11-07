"""Shared style for the Fig. 10 variants (A to D).

Okabe-Ito colours: AXIOM #0072B2, learned baselines #7F7F7F (filled markers), rules #D55E00 (hollow markers).
Liberation Sans (metric clone of Arial) at 8 pt everywhere, lines at least 0.5 pt, TrueType fonts in the PDF, no
background fills. Width is the WPC template's \\textwidth, measured with a pdflatex probe of sn-jnl.cls
(\\the\\textwidth = 372.0pt = 130.7 mm).
"""
import os

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEXTWIDTH_PT = 372.0
WIDTH_MM = TEXTWIDTH_PT / 72.27 * 25.4          # 130.7 mm
WIDTH_IN = WIDTH_MM / 25.4
FS = 8
LW = 0.6                                        # default line width, >= 0.5 pt

AX, LEARN, RULE = "#0072B2", "#7F7F7F", "#D55E00"
INK, FAINT = "#222222", "#BBBBBB"
ORDER = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static", "rule_local"]
NAME = {"axiom2": "AXIOM", "mappo_tuned": "MAPPO", "single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I",
        "rule_static": "Static rule", "rule_local": "Tuned rule"}
LEARNED = ORDER[:4]
RULES = ORDER[4:]
COLOR = {a: (AX if a == "axiom2" else LEARN if a in LEARNED else RULE) for a in ORDER}
MARKER = {"axiom2": "o", "mappo_tuned": "s", "single_agent_dqn": "^", "independent_dqn": "v",
          "rule_static": "D", "rule_local": "P"}


def marker_kw(a, ms=4.5):
    """Learned controllers filled, rules hollow."""
    c = COLOR[a]
    return dict(marker=MARKER[a], ms=ms, mec=c, mew=0.8, mfc=(c if a in LEARNED else "white"), ls="none")


def setup():
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
        "font.size": FS, "axes.titlesize": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
        "legend.fontsize": FS, "figure.titlesize": FS, "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
        "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
        "pdf.fonttype": 42, "ps.fonttype": 42, "lines.linewidth": LW, "axes.linewidth": LW,
        "xtick.major.width": LW, "ytick.major.width": LW, "xtick.minor.width": 0.5, "ytick.minor.width": 0.5,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.5, "ytick.minor.size": 1.5,
        "patch.linewidth": LW, "hatch.linewidth": 0.5, "axes.facecolor": "none", "savefig.facecolor": "white",
        "figure.facecolor": "white", "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
        "savefig.bbox": "standard", "savefig.pad_inches": 0.0, "axes.unicode_minus": True,
    })


# check, half and cross drawn as paths, since Liberation Sans has no check or half-circle glyphs
CHECK = Path([(-0.55, 0.0), (-0.15, -0.45), (0.6, 0.5)], [Path.MOVETO, Path.LINETO, Path.LINETO])


def status(ax, x, y, kind, color, ms=6.0, transform=None):
    tr = transform if transform is not None else ax.transData
    if kind == "yes":
        ax.plot([x], [y], marker=CHECK, ms=ms, mec=color, mfc="none", mew=1.1, ls="none", transform=tr, clip_on=False)
    elif kind == "half":
        ax.plot([x], [y], marker="o", ms=ms * 0.85, mec=color, mfc=color, fillstyle="left", mfcalt="white", mew=0.8,
                ls="none", transform=tr, clip_on=False)
    elif kind == "no":
        ax.plot([x], [y], marker="x", ms=ms * 0.75, mec=color, mew=1.0, ls="none", transform=tr, clip_on=False)
    elif kind == "nt":
        ax.plot([x], [y], marker="o", ms=ms * 0.85, mec=FAINT, mfc="white", mew=0.8, ls="none", transform=tr, clip_on=False)


def min_font(fig):
    """Smallest font size, in points at final size, of any visible text in the figure (size is never rescaled)."""
    fig.canvas.draw()
    sizes = [t.get_fontsize() for t in fig.findobj(mpl.text.Text) if t.get_visible() and t.get_text().strip()]
    return min(sizes) if sizes else None


def size_mm(fig):
    w, h = fig.get_size_inches()
    return float(round(w * 25.4, 1)), float(round(h * 25.4, 1))


def previews(png):
    """Greyscale (CIE L*) and deuteranopia (colorspacious, severity 100) versions of a rendered PNG."""
    from PIL import Image
    from colorspacious import cspace_convert
    im = np.asarray(Image.open(png).convert("RGB")).astype(float) / 255.0
    L = cspace_convert(im, "sRGB1", "CIELab")[..., 0] / 100.0
    Image.fromarray((np.clip(L, 0, 1) * 255).round().astype(np.uint8)).save(png.replace(".png", "_grey.png"), dpi=(300, 300))
    cvd = cspace_convert(im, {"name": "sRGB1+CVD", "cvd_type": "deuteranomaly", "severity": 100}, "sRGB1")
    Image.fromarray((np.clip(cvd, 0, 1) * 255).round().astype(np.uint8)).save(png.replace(".png", "_cvd.png"), dpi=(300, 300))


def save(fig, stem):
    """stem without extension, e.g. 'fig10_A'. Writes pdf, png (300 dpi), _grey.png and _cvd.png; returns facts."""
    base = os.path.join(HERE, stem)
    mf = min_font(fig)
    fig.savefig(base + ".pdf")
    fig.savefig(base + ".png", dpi=300)
    previews(base + ".png")
    facts = {"size_mm": size_mm(fig), "min_font_pt": mf}
    print(f"[{stem}] {facts}")
    return facts


def palette_check():
    """Pairwise CAM02-UCS distances of the three palette colours in colour, greyscale (L* only) and deuteranopia."""
    from colorspacious import cspace_convert, deltaE
    cols = {"AXIOM": AX, "learned": LEARN, "rules": RULE}
    rgb = {k: np.array(mpl.colors.to_rgb(v)) for k, v in cols.items()}
    out = {}
    for mode in ("colour", "grey", "deuteranopia"):
        conv = {}
        for k, v in rgb.items():
            if mode == "grey":
                L = cspace_convert(v, "sRGB1", "CIELab")[0]
                conv[k] = cspace_convert([L, 0, 0], "CIELab", "sRGB1")
            elif mode == "deuteranopia":
                conv[k] = np.clip(cspace_convert(v, {"name": "sRGB1+CVD", "cvd_type": "deuteranomaly", "severity": 100}, "sRGB1"), 0, 1)
            else:
                conv[k] = v
        ks = list(conv)
        out[mode] = {f"{a}-{b}": round(float(deltaE(conv[a], conv[b])), 1) for i, a in enumerate(ks) for b in ks[i + 1:]}
    return out
