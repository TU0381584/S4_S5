#!/usr/bin/env bash
# Builds the public-deposit archive in a staging directory. It does not upload anything.
# Usage: bash experiments/scripts/make_archive.sh <staging_dir>
# Tier 1 (code, configs, documents, pre-registrations, verification scripts, manuscript sources) is every git-tracked
# file outside experiments/results, experiments/logs and Papers_4-5/Paper_4. The console logs of experiments/logs,
# tracked or not, go in tier 2 as _console_logs.tar.zst. Tier 2 (stored evaluation logs and checkpoints) is each
# campaign directory of experiments/results as its own .tar.zst. SHA256SUMS covers every tarball.
set -euo pipefail
OUT="${1:?staging directory}"
cd "$(dirname "$0")/../.."
mkdir -p "$OUT/tier2_results"
git ls-files -z | grep -zv '^experiments/results/' | grep -zv '^experiments/logs/' | grep -zv '^Papers_4-5/Paper_4/' \
  | tar --null -T - -cf - | zstd -19 -T0 -q -o "$OUT/tier1_code_and_documents.tar.zst"
tar -C experiments -cf - logs | zstd -19 -T0 -q -o "$OUT/tier2_results/_console_logs.tar.zst"
git rev-parse HEAD > "$OUT/SOURCE_COMMIT.txt"
for d in experiments/results/*/; do
  n=$(basename "$d")
  tar -C experiments/results -cf - "$n" | zstd -6 -T0 -q -o "$OUT/tier2_results/$n.tar.zst"
done
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
echo "archive staged in $OUT"
