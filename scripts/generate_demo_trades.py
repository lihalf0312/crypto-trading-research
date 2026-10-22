"""Create a synthetic SQLite fixture; refuses to overwrite an existing file."""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyze_live import FIELDS, demo_trades


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb"):
            pass
    except OSError:
        parser.error("Choose a writable, unused output path.")
    try:
        with sqlite3.connect(target) as conn:
            conn.executescript((ROOT / "examples/trades_schema.sql").read_text())
            placeholders = ", ".join("?" for _ in FIELDS)
            conn.executemany(f"INSERT INTO trades ({', '.join(FIELDS)}) VALUES ({placeholders})",
                             [tuple(r[k] for k in FIELDS) for r in demo_trades()])
    except sqlite3.Error:
        print("Could not create synthetic SQLite fixture.", file=sys.stderr)
        return 2
    print("Created 12 entirely synthetic demo records. No strategy performance is represented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
