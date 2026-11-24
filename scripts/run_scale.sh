#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
make -s -C "$ROOT" morph_v15 >&2
echo "source,n,edges,degree_greedy,random_degree,improved_random_degree,minres,rss_mb,elapsed_ms,valid_flags"
for n in 32768 65536 131072 262144 524288 1048576; do
  "$ROOT/morph_v15" ba "$n" 100 1
done
