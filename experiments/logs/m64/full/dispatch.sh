#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m64/full
mkdir -p $D/claims
key=$(printf '%s' "$1" | md5sum | cut -c1-16)
mkdir "$D/claims/$key" 2>/dev/null || exit 0
case "$1" in m4*) until grep -q 'ALL A DONE' $D/progress.log && [ ! -f $D/extra_running ]; do sleep 30; done;; esac
exec $D/run_cmd.sh "$1"
