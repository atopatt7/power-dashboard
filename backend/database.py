"""SQLite database layer for power readings (stdlib only)."""
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional
from config import SQLITE_PATH, RETENTION_DAYS

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(SQLITE_PATH)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS power_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_name TEXT NOT NULL,
            value REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_device_time
        ON power_readings (device_name, timestamp)
    """)
    conn.commit()


def insert_readings(readings: list):
    """Insert a batch of power readings."""
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO power_readings (timestamp, device_name, value) VALUES (?, ?, ?)",
        [(r["timestamp"], r["device_name"], r["value"]) for r in readings],
    )
    conn.commit()


def query_readings(
    device: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 1000,
) -> list:
    """Query power readings with optional filters."""
    query = "SELECT timestamp, device_name, value FROM power_readings WHERE 1=1"
    params = []

    if device:
        query += " AND device_name = ?"
        params.append(device)
    if start:
        query += " AND timestamp >= ?"
        params.append(start)
    if end:
        query += " AND timestamp <= ?"
        params.append(end)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    conn = _get_conn()
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    return [
        {"timestamp": row["timestamp"], "device_name": row["device_name"], "value": row["value"]}
        for row in rows
    ]


def get_latest_readings() -> list:
    """Get the most recent reading for each device."""
    query = """
        SELECT device_name, timestamp, value
        FROM power_readings
        WHERE id IN (
            SELECT MAX(id) FROM power_readings GROUP BY device_name
        )
        ORDER BY device_name
    """
    conn = _get_conn()
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    return [
        {"timestamp": row["timestamp"], "device_name": row["device_name"], "value": row["value"]}
        for row in rows
    ]


def cleanup_old_data():
    """Remove readings older than RETENTION_DAYS."""
    cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
    conn = _get_conn()
    conn.execute("DELETE FROM power_readings WHERE timestamp < ?", (cutoff,))
    conn.commit()
