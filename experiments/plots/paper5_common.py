"""Shared plotting infrastructure for paper #5's M2/M3 figures --
separate from common.py (paper #4's already-finalized figure set) so
nothing here can perturb Papers_4-5/Paper_4's existing, submitted plots.
Reuses common.py's IEEE column-width/font rcParams unchanged (same
journal-figure sizing convention) and follows the dataviz skill's
validated default categorical palette: gat_ctde/independent_dqn/
single_agent_dqn take slots 1-3 (blue/orange/aqua), the specific triple
the palette's own documentation certifies passes the strict all-pairs
CVD/contrast gate (not just the looser adjacent-pairs one bar/line charts
normally need) -- chosen deliberately conservative since these 3 arms
are directly compared throughout the results section.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib as mpl
import numpy as np

from common import IEEE_COLUMN_WIDTH_IN  # noqa: F401 -- re-exported for figure scripts

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from m2_correctness_metrics import bootstrap_ci  # noqa: E402,F401 -- re-exported for figure scripts, not reimplemented

mpl.rcParams.update({
    "figure.figsize": (IEEE_COLUMN_WIDTH_IN, IEEE_COLUMN_WIDTH_IN * 0.75),
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "lines.linewidth": 1.2,
    "lines.markersize": 5,
    "axes.linewidth": 0.6,
    "axes.grid": True,
    "grid.linewidth": 0.4,
    "grid.alpha": 0.4,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.bbox": "tight",
})

# Printed widths for WPC (sn-jnl text block 372 pt) and Online Resource 1 (A4, 2.5 cm margins).
# Figures are drawn at these widths so every label prints at 8 pt or more, as Springer asks.
MAIN_WIDTH_IN = 372.0 / 72.27
SUPP_WIDTH_IN = 453.5 / 72.27


# Boxed, colour-coded environment tags, the style of the AXIOM superiority figure (fill, edge, text).
ENV_TAG = {"A": dict(fc="#e2e8f0", ec="#5a6b82", tc="#26344a"), "B": dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")}


def env_tag(ax, env, anchor=None, fontsize=8.5):
    """Environment tag beside a panel letter (anchor = the letter's text artist), else just above the
    panel's top-left corner. Pass fontsize so the tag prints at about 8.5 pt once the figure is scaled."""
    t = ENV_TAG[env]
    kw = dict(fontsize=fontsize, color=t["tc"], ha="left", annotation_clip=False,
              bbox=dict(boxstyle="round,pad=0.25", fc=t["fc"], ec=t["ec"], lw=0.6))
    if anchor is not None:
        return ax.annotate(f"Env {env}", xy=(1, 0.5), xycoords=anchor, xytext=(6, 0), textcoords="offset points", va="center", **kw)
    return ax.annotate(f"Env {env}", xy=(0, 1), xycoords="axes fraction", xytext=(0, 6), textcoords="offset points", va="bottom", **kw)


def panel(ax, letter, env=None, tag_size=8.5, **kw):
    """Bare panel letter, the Springer convention, with the environment tag beside it when env is given;
    the caption carries the description."""
    t = ax.set_title(letter, loc="left", fontsize=9, **kw)
    if env is not None:
        env_tag(ax, env, anchor=t, fontsize=tag_size)


M2_ARM_ORDER: List[str] = ["gat_ctde", "independent_dqn", "single_agent_dqn"]
M2_ARM_STYLE: Dict[str, dict] = {
    "gat_ctde":         {"color": "#2a78d6", "marker": "o", "label": "AXIOM (proposed)"},
    "independent_dqn":  {"color": "#eb6834", "marker": "^", "label": "DQN-I"},
    "single_agent_dqn": {"color": "#1baf7a", "marker": "s", "label": "DQN-SA"},
}

# M64/M65 arms: AXIOM v2 reuses AXIOM's style; MAPPO and the rules get their own.
M2_ARM_STYLE["axiom2"] = dict(M2_ARM_STYLE["gat_ctde"])
M2_ARM_STYLE["axiom2_mlp"] = {"color": "#8fb8ea", "marker": "o", "label": "AXIOM, MLP encoder"}
M2_ARM_STYLE["mappo_tuned"] = {"color": "#7a4fd0", "marker": "D", "label": "MAPPO"}
M2_ARM_STYLE["axiom"] = {"color": "#9aa0a6", "marker": "o", "label": "AXIOM, original"}
RULE_STYLE = {
    "rule_static": {"color": "#5b5a52", "marker": "v", "label": "Rule, shed all mMTC"},
    "rule_accept_all": {"color": "#c3c2b7", "marker": "^", "label": "Rule, accept all"},
    "rule_local": {"color": "#8a7a3a", "marker": "<", "label": "Rule, tuned local"},
    "rule_neighbour": {"color": "#b39a3c", "marker": ">", "label": "Rule, tuned neighbour-aware"},
}

M3_STYLE: Dict[str, dict] = {
    "centralized": {"color": "#2a78d6", "marker": "o", "label": "Centralised (AXIOM)"},
    "federated":   {"color": "#eb6834", "marker": "D", "label": "Federated, no DP ($\\sigma$=0)"},
    "curve":       {"color": "#2a78d6", "marker": "o", "label": "Federated AXIOM"},
}

# M4 shows all four arms together (unlike M3's Fig. 4, which only ever
# pairs gat_ctde against federated, so reusing independent_dqn's orange
# for federated there is harmless) -- federated needs its OWN slot here to
# avoid colliding with independent_dqn's orange. Slot 4 (yellow) of the
# dataviz skill's validated categorical order, next after gat_ctde/
# independent_dqn/single_agent_dqn's slots 1-3; gat_ctde/independent_dqn/
# single_agent_dqn keep their established colors unchanged for identity
# consistency across every figure in the paper.
M4_ARM_ORDER: List[str] = ["gat_ctde", "independent_dqn", "single_agent_dqn", "fl_gat_ctde_sigma0.0"]
M4_ARM_STYLE: Dict[str, dict] = {
    "gat_ctde":            M2_ARM_STYLE["gat_ctde"],
    "independent_dqn":     M2_ARM_STYLE["independent_dqn"],
    "single_agent_dqn":    M2_ARM_STYLE["single_agent_dqn"],
    "fl_gat_ctde_sigma0.0": {"color": "#eda100", "marker": "D", "label": "Federated AXIOM"},
}

# Fixed (never themed) status roles, dataviz skill palette.md -- used for
# paired win/tie/loss outcome coloring, never for series identity, so a
# status color never impersonates an arm's own categorical hue.
STATUS_COLORS: Dict[str, str] = {
    "good": "#0ca30c",
    "critical": "#d03b3b",
    "neutral": "#898781",
}


def load_m2_campaign(results_path: str) -> Tuple[List[int], Dict[str, Dict[str, dict]]]:
    with open(results_path) as fh:
        data = json.load(fh)
    seed_groups = data["seed_groups"]
    all_seeds = [s for g in seed_groups for s in g]
    return all_seeds, data["results"]


def load_m3_campaign(results_path: str) -> Tuple[List[int], Dict[str, Dict[str, dict]]]:
    with open(results_path) as fh:
        data = json.load(fh)
    return data["seeds"], data["results"]


def eval_omega_path(campaign_dir: str, arm_or_tag: str, seed: int) -> Path:
    """Handles the one real path-shape difference between arms:
    single_agent_dqn nests under dqn/offline_eval/rep_0/ (mc_runner.run_mc's
    own convention) while gat_ctde/independent_dqn/the M3 FL arm write a
    flat eval/omega_log.jsonl directly (marl_training.run_episodes_marl's
    convention)."""
    base = Path(campaign_dir) / arm_or_tag / f"seed{seed}" / "eval"
    flat = base / "omega_log.jsonl"
    if flat.exists():
        return flat
    return base / "dqn" / "offline_eval" / "rep_0" / "omega_log.jsonl"
