#!/usr/bin/env python3
"""M104 runner (docs/PAPER5_M104_preregistration.md): the M102 encoder variant named in M102_VARIANT, trained exactly
as m64_run.py trains AXIOM, with M67's validation-based checkpoint selection (m67_run.py, variant V1, unchanged).
Each run therefore writes both evaluations: eval_last/ (the last checkpoint, as every reported campaign evaluates)
and eval/ (the checkpoint with the best greedy score on 10 validation episodes of stream 20000 + seed, from snapshots
at episodes 100, 125, ..., 300). At --n 37 the 37-gNB layout and config come from m73_run.install(), as in M73.
Usage (cwd framework/): M102_VARIANT=gat m104_run.py --arm axiom2 --env A --n 37 --topology hex --seeds 9940 --out-dir ...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
import m67_run  # noqa: E402   (hooks snapshot saving into every value-based policy class on import)
import m102_variants as V  # noqa: E402

if __name__ == "__main__":
    v = os.environ.get("M102_VARIANT")
    if v not in V.VARIANTS:
        raise SystemExit(f"M102_VARIANT must be one of {sorted(V.VARIANTS)}, got {v!r}")
    if "--n" in sys.argv and sys.argv[sys.argv.index("--n") + 1] == "37":
        import m73_run
        m73_run.install()
    m64_run.AxiomV2Policy = V.VARIANTS[v]
    m64_run.run_learned = m67_run.run_learned_selected
    print(f"[m104] encoder variant {v}, validation-based checkpoint selection {m67_run.VARIANT}", flush=True)
    m64_run.main()
