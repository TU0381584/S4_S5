#!/bin/bash
tag=$1; shift
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 M63_BACKLOG_RESET=1 M63_PER_GNB_VIOLATION=1
cd /home/kmanojp/oranslice_rig/framework
../venv/bin/python3 ../experiments/scripts/m62_shared_env.py m6_run_experiment "$@" > ../experiments/logs/m63/$tag.log 2>&1
echo "$(date +%H:%M:%S) done $tag exit=$?" >> ../experiments/logs/m63/progress.log
