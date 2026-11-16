#!/bin/bash
# one M110 job: "<n> <topology> <arm> <seeds...>" (restart-safe: the runner skips seeds whose row.json exists)
set -- $1; n=$1; t=$2; arm=$3; shift 3
cd /home/kmanojp/oranslice_rig/framework
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 M75_PERGNB=1
name="A${n}_${t}_${arm}_$1"
../venv/bin/python3 ../experiments/scripts/m110_pergnb.py --n $n --topology $t --arm $arm --seeds "$@" > ../experiments/logs/m110/$name.log 2>&1
echo "$name exit $? $(date '+%H:%M:%S')" >> ../experiments/logs/m110/done.txt
