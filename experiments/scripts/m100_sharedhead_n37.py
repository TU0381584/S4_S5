#!/usr/bin/env python3
"""M100: the M70 shared-head AXIOM variant at 37 gNBs (docs/PAPER5_M100_preregistration.md). Composes two existing,
unmodified pieces: m73_run.install() for the 37-gNB hex layout and config, and m70_run.SharedHeadAxiom.
Usage (cwd framework/): same arguments as m73_run.py, e.g. --arm axiom2 --env A --n 37 --topology hex --seeds 8000 --out-dir ..."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402
import m70_run  # noqa: E402
import m64_run  # noqa: E402

if __name__ == "__main__":
    m73_run.install()
    m64_run.AxiomV2Policy = m70_run.SharedHeadAxiom
    print("[m100] AXIOM variant sharedhead at N=37", flush=True)
    m64_run.main()
