#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p user_data/data/binance
image='freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db'
# A fresh download includes the 240-hour indicator warmup. Optional arguments
# are forwarded to Freqtrade, e.g. --prepend when filling an older missing range.
docker run --rm --user "$(id -u):$(id -g)" --entrypoint freqtrade \
  -v "$PWD/user_data/data:/freqtrade/user_data/data" \
  -v "$PWD/configs/research.example.json:/freqtrade/research.example.json:ro" \
  "$image" download-data --config /freqtrade/research.example.json \
  --datadir /freqtrade/user_data/data/binance --trading-mode futures \
  --timeframes 1h 5m --timerange 20221222-20260902 --data-format-ohlcv feather "$@"
