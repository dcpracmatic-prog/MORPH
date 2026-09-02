#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
make -C "$ROOT" all
for f in "$ROOT"/datasets/*.gph; do
  echo "TEST $f"
  out=$("$ROOT/morph_qoblib_solver" "$f" morph 10 1)
  echo "$out"
  [[ "$(echo "$out" | cut -d, -f5)" == "1" ]]
done
echo "SMOKE TEST: PASS"
