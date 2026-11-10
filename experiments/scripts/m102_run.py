#!/usr/bin/env python3
"""M102/M103 runner: m64_run.py with AXIOM's policy class replaced by the encoder variant named in M102_VARIANT
(m102_variants.VARIANTS), run as --arm axiom2. At --n 37 it first applies m73_run.install() (the 37-gNB hex layout
and config), as M73 and M96 did. Nothing else changes.
Usage (cwd framework/): M102_VARIANT=gated m102_run.py --arm axiom2 --n 7 --topology ring --seeds 2100 --out-dir ...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
import m102_variants as V  # noqa: E402

if __name__ == "__main__":
    v = os.environ.get("M102_VARIANT")
    if v not in V.VARIANTS:
        raise SystemExit(f"M102_VARIANT must be one of {sorted(V.VARIANTS)}, got {v!r}")
    if "--n" in sys.argv and sys.argv[sys.argv.index("--n") + 1] == "37":
        import m73_run
        m73_run.install()
    m64_run.AxiomV2Policy = V.VARIANTS[v]
    print(f"[m102] encoder variant {v}", flush=True)
    m64_run.main()
