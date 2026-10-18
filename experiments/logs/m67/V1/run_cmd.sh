#!/bin/bash
tag="${1%%|*}"; cmd="${1#*|}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 M63_BACKLOG_RESET=1 M64_AXIOM_V2=1 M67_VARIANT=V1
D=/home/kmanojp/oranslice_rig/experiments/logs/m67/V1
cd /home/kmanojp/oranslice_rig/framework
../venv/bin/python3 $cmd > $D/p_$tag.log 2>&1
rc=$?
echo "$(date +%H:%M:%S) done p_$tag exit=$rc" >> $D/progress.log
