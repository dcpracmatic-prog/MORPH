#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
make -C "$ROOT" morph_v15
for n in 32768 65536 131072 262144 524288 1048576; do
  "$ROOT/morph_v15" "$n" 100 1
done
