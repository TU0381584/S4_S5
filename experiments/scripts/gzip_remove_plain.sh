#!/usr/bin/env bash
# Remove a plain log only if its .gz copy still decompresses to the sha256 recorded
# when the copy was made (gzip_verified.sh). Input lines: "OK <path> <sha256>".
read -r tag f h <<< "$1"
[ "$tag" = OK ] || exit 0
[ -f "$f" ] && [ -f "$f.gz" ] || { echo "MISSING $f"; exit 0; }
h2=$(gzip -dc "$f.gz" | sha256sum | cut -d' ' -f1)
[ "$h" = "$h2" ] && rm "$f" && echo "REMOVED $f" || echo "KEPT $f"
