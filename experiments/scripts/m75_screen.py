#!/usr/bin/env python3
"""M75 E: the pre-registered validation screen (m63_validation_screen.py, unchanged) on the
M73 checkpoints at 37 gNBs. The wrapper registers the N=37 config and hex layout and swaps in
the gzip-aware log reader of m66_verify.py; the screen's criteria are untouched. Descriptive only.

Usage (cwd = framework/): same arguments as m63_validation_screen.py, with --n 37.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402
import m63_validation_screen as scr  # noqa: E402
from m66_verify import find_eval, read  # noqa: E402

m73_run.install()
scr.CONFIGS[37] = m73_run.N37_CONFIG
RES = "/home/kmanojp/oranslice_rig/experiments/results/"
scr.eval_log = lambda cell, arm, s: find_eval(os.path.abspath(cell).replace(RES, ""), arm, s)
scr.seed_metrics = read

if __name__ == "__main__":
    scr.main()
