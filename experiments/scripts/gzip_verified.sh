#!/usr/bin/env bash
# Lossless gzip of one file: the plain file is removed only if the decompressed
# copy hashes identically and GZ_REMOVE=1. Prints "OK <path> <sha256>" or "FAIL <path>".
f="$1"
[ -f "$f" ] || { echo "SKIP $f"; exit 0; }
[ -e "$f.gz" ] && { echo "EXISTS $f.gz"; exit 0; }   # never overwrite
h1=$(sha256sum "$f" | cut -d' ' -f1)
gzip -c -6 "$f" > "$f.gz.tmp" || { rm -f "$f.gz.tmp"; echo "FAIL $f"; exit 0; }
h2=$(gzip -dc "$f.gz.tmp" | sha256sum | cut -d' ' -f1)
if [ "$h1" = "$h2" ] && gzip -t "$f.gz.tmp"; then
  touch -r "$f" "$f.gz.tmp" && mv "$f.gz.tmp" "$f.gz" && { [ "${GZ_REMOVE:-0}" = 1 ] && rm "$f"; true; } && echo "OK $f $h1"
else
  rm -f "$f.gz.tmp"; echo "FAIL $f"
fi
