"""Peak demand forecast module.

Algorithm:
  1. Load pre-computed per-5-minute bucket statistics (median / P25 / P75)
     from historical data (backend/data/bucket_stats.json).
  2. Query the last 30 min of live readings from SQLite to compute a
     correction ratio  (actual_avg / historical_avg for the same window).
  3. Apply correction to next FORECAST_HOURS of 5-minute medians.
  4. Return forecast list + metadata.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────
STATS_FILE     = os.path.join(os.path.dirname(__file__), "data", "bucket_stats.json")
RESAMPLE_MIN   = 5          # bucket width (minutes)
FORECAST_HOURS = 4          # how far ahead to predict
TW_TZ          = timezone(timedelta(hours=8))

# Module-level cache so we only read the JSON once per process
_bucket_stats: dict | None = None


def _load_stats() -> dict:
    """Load (and cache) bucket statistics from JSON."""
    global _bucket_stats
    if _bucket_stats is not None:
        return _bucket_stats

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Keys are stored as strings in JSON; convert to int
    _bucket_stats = {int(k): v for k, v in raw.items()}
    logger.info(f"Loaded {len(_bucket_stats)} bucket stats from {STATS_FILE}")
    return _bucket_stats


def _get_live_correction() -> float:
    """Compare live SQLite average to historical average for same window.

    Returns a ratio clamped to [0.5, 2.0] so we never extrapolate wildly.
    Returns 1.0 if live data is unavailable.
    """
    try:
        from database import query_readings  # local import to avoid circular deps

        start_utc = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        recent = query_readings(start=start_utc, limit=50000)
        if not recent:
            return 1.0

        # Sum all devices per timestamp → factory total
        ts_map: dict[str, float] = {}
        for r in recent:
            ts = r["timestamp"]
            ts_map[ts] = ts_map.get(ts, 0.0) + r["value"]

        if not ts_map:
            return 1.0

        live_avg = sum(ts_map.values()) / len(ts_map)

        # Historical average for the same 30-minute window
        stats = _load_stats()
        now_tw = datetime.now(TW_TZ)
        hist_values = []
        for i in range(0, 30, RESAMPLE_MIN):
            ref = now_tw - timedelta(minutes=i)
            bucket = (ref.hour * 60 + ref.minute) // RESAMPLE_MIN * RESAMPLE_MIN
            if bucket in stats:
                hist_values.append(stats[bucket]["mean"])

        if not hist_values:
            return 1.0

        hist_avg = sum(hist_values) / len(hist_values)
        if hist_avg <= 0:
            return 1.0

        ratio = live_avg / hist_avg
        return max(0.5, min(2.0, ratio))  # clamp

    except Exception as e:
        logger.warning(f"Could not compute correction ratio: {e}")
        return 1.0


def get_forecast(threshold: float = 700.0, hours: int = FORECAST_HOURS) -> dict:
    """Return a forecast dict for the next `hours` hours.

    Response shape:
    {
        "generated_at": "YYYY-MM-DD HH:MM:SS",
        "threshold":    700,
        "correction_ratio": 1.05,
        "forecast": [
            {"time": "14:30", "minute": 870, "value": 412.3,
             "p25": 350.0, "p75": 480.0, "over_threshold": false},
            ...
        ]
    }
    """
    stats = _load_stats()
    now_tw = datetime.now(TW_TZ)
    correction = _get_live_correction()

    num_slots = hours * 60 // RESAMPLE_MIN
    forecast = []

    for i in range(1, num_slots + 1):
        future_dt = now_tw + timedelta(minutes=i * RESAMPLE_MIN)
        future_minute = future_dt.hour * 60 + future_dt.minute
        future_bucket = (future_minute // RESAMPLE_MIN) * RESAMPLE_MIN

        if future_bucket in stats:
            s = stats[future_bucket]
            predicted = s["median"] * correction
            p25       = s["p25"]    * correction
            p75       = s["p75"]    * correction
        else:
            # Fallback: global median
            all_medians = [v["median"] for v in stats.values()]
            predicted = (sum(all_medians) / len(all_medians)) * correction
            p25 = predicted * 0.85
            p75 = predicted * 1.15

        forecast.append({
            "time":          future_dt.strftime("%H:%M"),
            "minute":        future_minute,
            "value":         round(predicted, 1),
            "p25":           round(p25, 1),
            "p75":           round(p75, 1),
            "over_threshold": predicted > threshold,
        })

    return {
        "generated_at":    now_tw.strftime("%Y-%m-%d %H:%M:%S"),
        "threshold":       threshold,
        "correction_ratio": round(correction, 3),
        "forecast":        forecast,
    }
