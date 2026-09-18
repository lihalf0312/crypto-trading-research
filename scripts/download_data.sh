#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p user_data/data

docker run --rm \
  --entrypoint freqtrade \
  -v "$PWD/user_data/data:/freqtrade/user_data/data" \
  freqtradeorg/freqtrade:stable \
  download-data \
  --exchange binance \
  --trading-mode futures \
  --candle-types futures \
  --pairs BTC/USDT:USDT \
  --timeframes 5m \
  --timerange 20230901-20260917 \
  --data-format-ohlcv feather \
  --datadir /freqtrade/user_data/data
