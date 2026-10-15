#!/bin/bash
# line format: J:<arm|cond|seeds>  or  C:<tag|cmd>
# Claim lock: each job line runs once even when two worker pools share the list.
D=/home/kmanojp/oranslice_rig/experiments/logs/m63/full
mkdir -p $D/claims
key=$(printf '%s' "$1" | md5sum | cut -c1-16)
mkdir "$D/claims/$key" 2>/dev/null || exit 0
# disruption jobs read phase-A checkpoints; wait until the extra worker pool has drained too
case "$1" in C:m4*) until grep -q 'extra worker done' $D/progress.log; do sleep 30; done;; esac
case "$1" in J:*) exec ./run_job.sh "${1#J:}";; C:*) exec ./run_cmd.sh "${1#C:}";; esac
