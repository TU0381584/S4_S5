#!/bin/bash
# usage: run.sh <tag> <args...>
tag=$1; shift
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd /home/kmanojp/oranslice_rig/framework
../venv/bin/python3 ../experiments/scripts/m62_reviewer_experiments.py "$@" > ../experiments/logs/m63/$tag.log 2>&1
echo "$(date +%H:%M:%S) done $tag exit=$?" >> ../experiments/logs/m63/progress.log
