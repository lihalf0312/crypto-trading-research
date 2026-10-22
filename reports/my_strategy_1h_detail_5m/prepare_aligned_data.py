"""Build a separate consistency control; never replace the original 1h signals."""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "user_data/data/binance/futures"
TARGET = ROOT / "user_data/data/binance_aligned/futures"
TARGET.mkdir(parents=True, exist_ok=True)
config = json.loads((ROOT / "configs/research.example.json").read_text())
manifest = []
for pair in config["exchange"]["pair_whitelist"]:
    stem = pair.replace("/", "_").replace(":", "_")
    detail = pd.read_feather(SOURCE / f"{stem}-5m-futures.feather").set_index("date")
    counts = detail.resample("1h").size()
    hourly = detail.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    hourly = hourly.loc[counts == 12]
    hourly.reset_index().to_feather(TARGET / f"{stem}-1h-futures.feather")
    manifest.append(dict(pair=pair,
                         one_hour_sha256=hashlib.sha256((TARGET / f"{stem}-1h-futures.feather").read_bytes()).hexdigest(),
                         five_minute_sha256=hashlib.sha256((SOURCE / f"{stem}-5m-futures.feather").read_bytes()).hexdigest()))
    for suffix in ["5m-futures", "1h-mark", "1h-funding_rate"]:
        name = f"{stem}-{suffix}.feather"
        target = TARGET / name
        if not target.exists():
            os.link(SOURCE / name, target)
print(f"Built aligned hourly data for {len(config['exchange']['pair_whitelist'])} pairs.")
(HERE / "aligned_data_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
