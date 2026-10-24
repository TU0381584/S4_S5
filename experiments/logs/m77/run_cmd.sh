#!/bin/bash
# job line: tag|ENV=VAL [ENV=VAL ...] (optional)|script args
tag="${1%%|*}"; rest="${1#*|}"; envs="${rest%%|*}"; cmd="${rest#*|}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 M63_BACKLOG_RESET=1 M64_AXIOM_V2=1
[ -n "$envs" ] && export $envs
D=/home/kmanojp/oranslice_rig/experiments/logs/m77
cd /home/kmanojp/oranslice_rig/framework
../venv/bin/python3 $cmd > $D/p_$tag.log 2>&1
rc=$?
echo "$(date +%H:%M:%S) done p_$tag exit=$rc" >> $D/progress.log
