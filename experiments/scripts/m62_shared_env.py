#!/usr/bin/env python3
"""Run an existing campaign runner (m6/m3/m4_run_experiment.py) against the
M62 shared-budget simulator instead of ClosedLoopKpmSource.

Same technique as m27_scaling_reframe.py: import the runner as a module,
reassign its module-global make_kpm_source_factory (resolved at call time),
then hand control to its own main() with the remaining CLI arguments. The
runners themselves and the frozen framework are not edited.

Usage (cwd = framework/):
    ../venv/bin/python3 ../experiments/scripts/m62_shared_env.py m6_run_experiment \
        --config-path ... --topology ring --seeds 900 901 --out-dir ...
"""
import importlib
import sys

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

from shared_budget_kpm_source import make_shared_budget_factory  # noqa: E402


def shared_factory(cfg, sd_for_slice, gnb_load_multiplier_mode="default"):
    if gnb_load_multiplier_mode not in ("default",):
        raise ValueError("the shared-budget simulator only supports the default load-multiplier mode")
    return make_shared_budget_factory(cfg, sd_for_slice)


if __name__ == "__main__":
    module = importlib.import_module(sys.argv[1])
    # patch the entry module and every campaign runner it pulled in (e.g. m4_seed_campaign -> m4_run_experiment)
    for name in [sys.argv[1], "m2_run_experiment", "m3_run_experiment", "m4_run_experiment", "m6_run_experiment"]:
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "make_kpm_source_factory"):
            mod.make_kpm_source_factory = shared_factory
    import os
    if os.environ.get("M62_ENCODER") == "mlp":
        # GAT-to-MLP ablation inside an existing runner: swap the policy class it constructs
        from m62_reviewer_experiments import MlpCtdeMarlPolicy
        for name in [sys.argv[1], "m6_run_experiment"]:
            mod = sys.modules.get(name)
            if mod is not None and hasattr(mod, "GatCtdeMarlPolicy"):
                mod.GatCtdeMarlPolicy = MlpCtdeMarlPolicy
        print("[m62-shared-env] encoder swapped to per-node MLP (ablation)", flush=True)
    if os.environ.get("M63_PER_GNB_VIOLATION") == "1":
        from m62_reviewer_experiments import install_per_gnb_violation
        install_per_gnb_violation()
    if os.environ.get("M63_BACKLOG_RESET") == "1":
        from m62_reviewer_experiments import install_backlog_reset
        install_backlog_reset()
    sys.argv = [sys.argv[1] + ".py"] + sys.argv[2:]
    print(f"[m62-shared-env] {sys.argv[0]} running on the shared-budget simulator", flush=True)
    module.main()
