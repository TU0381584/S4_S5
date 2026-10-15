#!/bin/bash
IFS='|' read -r arm cond seeds <<< "$1"
tag="${arm}_${cond}_$(echo $seeds | cut -d' ' -f1)"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd /home/kmanojp/oranslice_rig/framework
../venv/bin/python3 ../experiments/scripts/m62_reviewer_experiments.py --env shared --backlog-reset --arm $arm --condition $cond \
  --seeds $seeds --train-episodes 300 --eval-episodes 50 \
  --out-dir ../experiments/results/m63_reviewer/$cond > ../experiments/logs/m63/full/$tag.log 2>&1
echo "$(date +%H:%M:%S) done $tag exit=$?" >> ../experiments/logs/m63/full/progress.log
