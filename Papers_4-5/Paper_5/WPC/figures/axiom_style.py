"""Shared style for every AXIOM figure (main paper and Online Resource 1), after the frozen Fig. 10.

Tokens follow Fig. 10 (experiments/plots/paper5_fig_capability.py, frozen): Okabe-Ito colours, learned controllers
as filled markers, rules as hollow markers, AXIOM in blue, learned baselines in grey, rules in vermillion; marker
shape always distinguishes controllers, so no figure depends on colour alone. Maps use cividis.

Limits from the figure-audit brief: widths 84 mm or full width, kept at 119 mm by the author's decision (the brief's
174 mm exceeds the text block), 8 pt sans text and
never below 7 pt, lines at least 0.3 pt, no background tints, PDF and EPS with embedded TrueType fonts.
NOTE: the sn-jnl text block is 130.7 mm wide (\\textwidth = 372 pt, measured); a 174 mm figure is wider than the
text block. See CHANGELOG.md, Phase 0.

Usage:
    import axiom_style as S
    S.setup()
    fig = S.figure("col", height_mm=60)          # or "full"
    S.strip_ci(ax, y, values, "axiom2")
    S.save(fig, "figures/Fig7")                  # checks, then writes Fig7.pdf and Fig7.eps
"""
import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

# ------------------------------------------------------------------ sizes and limits
MM = 1 / 25.4
WIDTH_MM = {"col": 84.0, "full": 119.0}   # author decision 2026-11-08: keep the existing 119 mm, since 174 mm exceeds the 130.7 mm text block
FIG10_MM = 119.0                     # frozen exception
TEXTWIDTH_MM = 372.0 / 72.27 * 25.4  # 130.7, measured from sn-jnl
FONT_PT, MIN_FONT_PT, MIN_LINE_PT = 8.0, 7.0, 0.3
MIN_GAP_MM = 0.4                     # minimum clearance between two text labels

# ------------------------------------------------------------------ colour and policy tokens (Okabe-Ito)
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7", "grey": "#7F7F7F"}
INK, FAINT = "#222222", "#BBBBBB"
POLICY = {
    # learned controllers: filled markers (as in Fig. 10)
    "axiom2":           dict(label="AXIOM",      color=OI["blue"],       marker="o", filled=True),
    "mappo_tuned":      dict(label="MAPPO",      color=OI["grey"],       marker="s", filled=True),
    "single_agent_dqn": dict(label="DQN-SA",     color=OI["grey"],       marker="^", filled=True),
    "independent_dqn":  dict(label="DQN-I",      color=OI["grey"],       marker="v", filled=True),
    "axiom2_mlp":       dict(label="AXIOM-MLP",  color=OI["sky"],        marker="o", filled=True),
    "vdn":              dict(label="VDN",        color=OI["green"],      marker="<", filled=True),
    # rules: hollow markers (as in Fig. 10)
    "rule_static":      dict(label="Static rule", color=OI["vermillion"], marker="D", filled=False),
    "rule_local":       dict(label="Tuned rule",  color=OI["vermillion"], marker="P", filled=False),
    "rule_local_transfer": dict(label="Tuned rule", color=OI["vermillion"], marker="P", filled=False),
    "rule_neighbour":   dict(label="Neighbour-aware rule", color=OI["vermillion"], marker="h", filled=False),
    "rule_retuned":     dict(label="Re-tuned rule", color=OI["vermillion"], marker="X", filled=False),
    "rule_accept_all":  dict(label="Accept-all",  color=OI["black"],      marker="o", filled=False),
}
ORDER = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static", "rule_local"]
MAP_CMAP = "cividis"
CAPTION_COLOUR_WORDS = ("red", "green", "blue", "orange", "yellow", "purple", "violet", "pink", "grey", "gray", "black",
                        "white", "cyan", "magenta", "vermillion", "brown", "teal", "dark", "light", "pale", "colour",
                        "color", "shaded", "tinted")


def setup():
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
        "font.size": FONT_PT, "axes.titlesize": FONT_PT, "axes.labelsize": FONT_PT, "xtick.labelsize": FONT_PT,
        "ytick.labelsize": FONT_PT, "legend.fontsize": FONT_PT, "mathtext.fontset": "custom",
        "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
        "pdf.fonttype": 42, "ps.fonttype": 42, "lines.linewidth": 0.6, "axes.linewidth": 0.6, "patch.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.minor.size": 1.5, "ytick.minor.size": 1.5,
        "hatch.linewidth": 0.4, "axes.facecolor": "none", "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
        "savefig.bbox": "standard", "savefig.pad_inches": 0.0, "axes.unicode_minus": True,
    })


def figure(width="col", height_mm=60.0):
    w = FIG10_MM if width == "fig10" else WIDTH_MM[width]
    return plt.figure(figsize=(w * MM, height_mm * MM))


def lighten(color, f=0.55):
    """Solid tint of a colour (f = share of white). EPS has no transparency, so per-seed dots use tints, not alpha."""
    c = np.array(mpl.colors.to_rgb(color))
    return tuple(1 - (1 - f) * (1 - c))


def marker_kw(policy, ms=4.0):
    p = POLICY[policy]
    return dict(marker=p["marker"], ms=ms, mec=p["color"], mew=0.8, mfc=p["color"] if p["filled"] else "white", ls="none")


# ------------------------------------------------------------------ statistics shared by every figure
def boot_ci(values, seed=0, n=10000):
    """95% percentile bootstrap CI of the mean (scipy.stats.bootstrap, default_rng(seed)), as in Fig. 10."""
    from scipy.stats import bootstrap
    v = np.asarray(list(values), float)
    if len(v) < 2 or np.all(v == v[0]):
        return float(v.mean()), float(v.mean())
    r = bootstrap((v,), np.mean, n_resamples=n, confidence_level=0.95, method="percentile",
                  random_state=np.random.default_rng(seed))
    return float(r.confidence_interval.low), float(r.confidence_interval.high)


def wilson(k, n, z=1.959963984540054):
    """Wilson score 95% interval for k successes in n trials."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(c - h), float(c + h)


# ------------------------------------------------------------------ drawing helpers
def strip_ci(ax, y, values, policy, rng=None, orient="h", jitter=0.22, ms=4.0, dots=True):
    """Fig. 10's strip: one tinted dot per seed, the 95% bootstrap CI as a bar, the mean as the policy's marker.
    Returns (mean, lo, hi, n)."""
    v = np.asarray(list(values), float)
    rng = rng if rng is not None else np.random.default_rng(0)
    m = float(v.mean()); lo, hi = boot_ci(v)
    col = POLICY[policy]["color"]
    j = y + rng.uniform(-jitter, jitter, len(v))
    if orient == "h":
        if dots:
            ax.scatter(v, j, s=1.4, c=[lighten(col)], lw=0, zorder=2)
        ax.plot([lo, hi], [y, y], color=col, lw=1.0, solid_capstyle="butt", zorder=3)
        ax.plot([m], [y], zorder=4, **marker_kw(policy, ms))
    else:
        if dots:
            ax.scatter(j, v, s=1.4, c=[lighten(col)], lw=0, zorder=2)
        ax.plot([y, y], [lo, hi], color=col, lw=1.0, solid_capstyle="butt", zorder=3)
        ax.plot([y], [m], zorder=4, **marker_kw(policy, ms))
    return m, lo, hi, len(v)


def hex_corners(cx, cy, r=1.0):
    """Flat-topped hexagon corners."""
    a = np.deg2rad(np.arange(0, 360, 60))
    return np.c_[cx + r * np.cos(a), cy + r * np.sin(a)]


def axial_to_xy(q, rr, r=1.0):
    """Axial hex coordinates to centre positions for flat-topped hexagons."""
    return 1.5 * r * q, np.sqrt(3) * r * (rr + q / 2)


def hexmap(ax, centres, values, vmin=0.0, vmax=1.0, cmap=MAP_CMAP, outline=(), r=1.0, edge="white"):
    """Hex map on cividis. values[i] is a number (one colour per cell) or a 3-tuple (three sectors, one per slice,
    starting at the top and going clockwise). Cells in `outline` get a dark rim. Returns a ScalarMappable for a
    shared colourbar."""
    norm = mpl.colors.Normalize(vmin, vmax); cm = mpl.colormaps[cmap]
    for i, ((x, y), v) in enumerate(zip(centres, values)):
        C = hex_corners(x, y, r)
        if np.ndim(v) == 0:
            ax.add_patch(Polygon(C, closed=True, fc=cm(norm(v)), ec=edge, lw=0.4))
        else:
            # three sectors of two triangles each: corners (0,1,2), (2,3,4), (4,5,0) around the centre
            for k, val in enumerate(v):
                pts = [(x, y), *C[[2 * k, 2 * k + 1, (2 * k + 2) % 6]]]
                ax.add_patch(Polygon(pts, closed=True, fc=cm(norm(val)), ec=edge, lw=0.3))
        if i in outline:
            ax.add_patch(Polygon(C, closed=True, fc="none", ec=INK, lw=1.0, zorder=5))
    ax.set_aspect("equal"); ax.axis("off")
    return mpl.cm.ScalarMappable(norm=norm, cmap=cm)


# ------------------------------------------------------------------ checks and output
def check(fig, allow=("col", "full")):
    """Raise on: width not in the allowed set, text below 7 pt, a line under 0.3 pt, overlapping or clipped labels."""
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    w_mm = fig.get_size_inches()[0] / MM
    ok_w = [WIDTH_MM[a] if a in WIDTH_MM else FIG10_MM for a in allow]
    assert any(abs(w_mm - w) < 0.05 for w in ok_w), f"width {w_mm:.1f} mm not in {ok_w}"
    # tick labels of ticks outside an axis's view are kept by matplotlib but never drawn; leave them out
    undrawn = set()
    for ax in fig.axes:
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = min(lim), max(lim)
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                if not (lo - 1e-9 <= tk.get_loc() <= hi + 1e-9):
                    undrawn.update({id(tk.label1), id(tk.label2)})
    ts = [t for t in fig.findobj(mpl.text.Text) if t.get_visible() and t.get_text().strip() and id(t) not in undrawn]
    small = [(t.get_text(), t.get_fontsize()) for t in ts if t.get_fontsize() < MIN_FONT_PT]
    assert not small, f"text below {MIN_FONT_PT} pt: {small[:5]}"
    thin = [a for a in fig.findobj(mpl.lines.Line2D) if a.get_visible() and a.get_linestyle() not in ("None", "none", "")
            and 0 < a.get_linewidth() < MIN_LINE_PT]
    assert not thin, f"{len(thin)} lines under {MIN_LINE_PT} pt"
    W, H = fig.bbox.width, fig.bbox.height
    pad = MIN_GAP_MM * MM * fig.dpi
    bb = [(t.get_text(), t.get_window_extent(rnd)) for t in ts]
    out = [s for s, b in bb if b.x0 < -0.5 or b.y0 < -0.5 or b.x1 > W + 0.5 or b.y1 > H + 0.5]
    assert not out, f"text outside the canvas: {out[:5]}"
    grow = lambda b: mpl.transforms.Bbox([[b.x0 - pad / 2, b.y0 - pad / 2], [b.x1 + pad / 2, b.y1 + pad / 2]])
    bad = [(a, c) for i, (a, b1) in enumerate(bb) for c, b2 in bb[i + 1:] if grow(b1).overlaps(grow(b2))]
    assert not bad, f"overlapping text: {bad[:5]}"
    return {"width_mm": round(w_mm, 1), "height_mm": round(fig.get_size_inches()[1] / MM, 1),
            "min_font_pt": min(t.get_fontsize() for t in ts) if ts else None}


def save(fig, stem, allow=("col", "full"), png=True):
    """Check, then write stem.pdf and stem.eps (TrueType embedded) and, for previews, stem.png at 300 dpi."""
    import os
    try:
        facts = check(fig, allow)
    except AssertionError:
        d = os.path.join(os.path.dirname(os.path.abspath(stem)), "audit_previews"); os.makedirs(d, exist_ok=True)
        fig.savefig(os.path.join(d, os.path.basename(stem) + "_layoutfail.png"), dpi=200)   # for inspection only
        raise
    fig.savefig(stem + ".pdf")
    fig.savefig(stem + ".eps")
    if png:
        fig.savefig(stem + ".png", dpi=300)
    return facts


def caption_colour_words(caption):
    """Colour words in a caption (the audit requires none)."""
    import re
    return [w for w in CAPTION_COLOUR_WORDS if re.search(rf"\b{w}\b", caption, re.I)]


def cvd_previews(png):
    """Greyscale (CIE L*) and three CVD simulations (deuteranomaly, protanomaly, tritanomaly; severity 100) of a PNG.
    Writes <stem>_grey.png, _deut.png, _prot.png, _trit.png into audit_previews/ beside it."""
    import os
    from PIL import Image
    from colorspacious import cspace_convert
    d = os.path.join(os.path.dirname(os.path.abspath(png)), "audit_previews"); os.makedirs(d, exist_ok=True)
    stem = os.path.join(d, os.path.basename(png)[:-4])
    im = np.asarray(Image.open(png).convert("RGB")).astype(float) / 255.0
    L = cspace_convert(im, "sRGB1", "CIELab")[..., 0] / 100.0
    Image.fromarray((np.clip(L, 0, 1) * 255).round().astype(np.uint8)).save(stem + "_grey.png")
    for t, tag in (("deuteranomaly", "deut"), ("protanomaly", "prot"), ("tritanomaly", "trit")):
        c = cspace_convert(im, {"name": "sRGB1+CVD", "cvd_type": t, "severity": 100}, "sRGB1")
        Image.fromarray((np.clip(c, 0, 1) * 255).round().astype(np.uint8)).save(stem + f"_{tag}.png")
    return stem


def token_separation(policies):
    """Pairwise CAM02-UCS distance of the policies' colours in colour, greyscale and three CVD simulations, and
    whether each pair also differs in marker shape or fill (the shape fallback the audit accepts)."""
    from colorspacious import cspace_convert, deltaE
    out = {}
    for i, a in enumerate(policies):
        for b in policies[i + 1:]:
            ca, cb = (np.array(mpl.colors.to_rgb(POLICY[p]["color"])) for p in (a, b))
            d = {"colour": float(deltaE(ca, cb))}
            La, Lb = (cspace_convert(c, "sRGB1", "CIELab")[0] for c in (ca, cb))
            d["grey_dL"] = float(abs(La - Lb))
            for t in ("deuteranomaly", "protanomaly", "tritanomaly"):
                sp = {"name": "sRGB1+CVD", "cvd_type": t, "severity": 100}
                d[t] = float(deltaE(np.clip(cspace_convert(ca, sp, "sRGB1"), 0, 1), np.clip(cspace_convert(cb, sp, "sRGB1"), 0, 1)))
            d["shape_differs"] = (POLICY[a]["marker"], POLICY[a]["filled"]) != (POLICY[b]["marker"], POLICY[b]["filled"])
            out[f"{a}|{b}"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()}
    return out
