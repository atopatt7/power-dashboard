"""Rebuild bucket_stats.json from historical Excel files.

Run this script whenever you add new historical data or change the
holiday exclusion list:

    python rebuild_stats.py

The script will:
  1. Load all Excel files listed in SOURCES
  2. Merge and deduplicate
  3. Exclude rows in HOLIDAY_RANGES
  4. Resample to 5-minute buckets and compute statistics
  5. Save to data/bucket_stats.json
"""

import json
import os
import sys
import pandas as pd
import numpy as np

# ── Configuration ──────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Historical Excel files to include (add new files here)
SOURCES = [
    os.path.join(DATA_DIR, "historical.xlsx"),   # 2026-02-07 ~ 2026-02-25
    os.path.join(DATA_DIR, "historical2.xlsx"),  # 2026-02-14 ~ 2026-03-05
]

# Periods to EXCLUDE from prediction training (e.g. holidays, shutdowns)
# Format: (start_inclusive, end_exclusive)
HOLIDAY_RANGES = [
    ("2026-02-13", "2026-02-24"),  # 春節假期 2/13–2/23
]

RESAMPLE_MIN = 5
OUT_FILE = os.path.join(DATA_DIR, "bucket_stats.json")

# ── Main ───────────────────────────────────────────────────────────

def main():
    print("Loading source files...")
    dfs = []
    for path in SOURCES:
        if not os.path.isfile(path):
            print(f"  [SKIP] {path} not found")
            continue
        df = pd.read_excel(path)
        df = df[df.iloc[:, 0].astype(str).str.match(r"\d{4}")].copy()
        df.columns = ["time", "power"]
        df["time"] = pd.to_datetime(df["time"])
        df = df.dropna(subset=["power"])
        dfs.append(df)
        print(f"  Loaded {len(df):,} rows from {os.path.basename(path)}")

    if not dfs:
        print("ERROR: No source files found.")
        sys.exit(1)

    combined = (
        pd.concat(dfs, ignore_index=True)
        .drop_duplicates(subset="time")
        .sort_values("time")
    )
    print(f"\nMerged: {len(combined):,} rows  ({combined['time'].min().date()} ~ {combined['time'].max().date()})")

    # Exclude holiday ranges
    mask = pd.Series([False] * len(combined), index=combined.index)
    for start_str, end_str in HOLIDAY_RANGES:
        s = pd.Timestamp(start_str)
        e = pd.Timestamp(end_str)
        mask |= (combined["time"] >= s) & (combined["time"] < e)

    clean = combined[~mask].copy()
    excluded = mask.sum()
    print(f"Excluded {excluded:,} holiday rows → {len(clean):,} rows remain")

    # 5-minute bucket statistics
    clean["minute"] = clean["time"].dt.hour * 60 + clean["time"].dt.minute
    clean["bucket"] = (clean["minute"] // RESAMPLE_MIN) * RESAMPLE_MIN

    stats = {}
    for bucket, group in clean.groupby("bucket"):
        vals = group["power"].values
        stats[int(bucket)] = {
            "median": round(float(np.median(vals)), 1),
            "p25":    round(float(np.percentile(vals, 25)), 1),
            "p75":    round(float(np.percentile(vals, 75)), 1),
            "mean":   round(float(np.mean(vals)), 1),
        }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f)

    print(f"\n✅ Saved {len(stats)} bucket stats → {OUT_FILE}")
    print("\nSample (08:00 / 12:00 / 18:00):")
    for b in [480, 720, 1080]:
        s = stats.get(b, {})
        print(f"  {b//60:02d}:00  median={s.get('median')} kW  P25={s.get('p25')}  P75={s.get('p75')}")


if __name__ == "__main__":
    main()
