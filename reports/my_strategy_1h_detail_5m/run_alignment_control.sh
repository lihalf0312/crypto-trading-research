#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
repo_root="$PWD"
image='freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db'
report='reports/my_strategy_1h_detail_5m'
docker run --rm --user "$(id -u):$(id -g)" --entrypoint python \
  -v "$repo_root:/workspace" "$image" "/workspace/$report/alignment_control.py"
