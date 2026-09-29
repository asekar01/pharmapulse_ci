"""
PharmaPulse CI — Cache Manager
==============================
Resilient, thread-safe SQLite disk cache with in-memory fallback.
Caches ClinicalTrials.gov, openFDA, and PubMed responses with a 24-hour TTL.
Ensures sub-second repeat queries and offline resilience.
"""

import sqlite3
import json
import time
import os
import threading
import logging

logger = logging.getLogger("pharmapulse.cache")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharmapulse_cache.db")
_mem_cache = {}
_lock = threading.Lock()

def _init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    source TEXT,
                    data_json TEXT,
                    created_at REAL
                )
            """)
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not initialize SQLite cache, using in-memory cache: {e}")

_init_db()

def get_cached(key: str, max_age_hours: float = 24.0):
    """Retrieve data from SQLite cache if within max_age_hours."""
    now = time.time()
    max_age_sec = max_age_hours * 3600.0

    with _lock:
        # Check memory first
        if key in _mem_cache:
            entry = _mem_cache[key]
            if now - entry["created_at"] < max_age_sec:
                return entry["data"]

        # Check SQLite
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT data_json, created_at FROM api_cache WHERE cache_key = ?", (key,))
                row = cur.fetchone()
                if row:
                    data_json, created_at = row
                    if now - created_at < max_age_sec:
                        data = json.loads(data_json)
                        _mem_cache[key] = {"data": data, "created_at": created_at}
                        return data
        except Exception as e:
            logger.debug(f"Cache read error for key {key}: {e}")

    return None

def set_cache(key: str, source: str, data):
    """Save data to both SQLite and memory cache."""
    now = time.time()
    try:
        data_json = json.dumps(data)
    except Exception:
        return

    with _lock:
        _mem_cache[key] = {"data": data, "created_at": now}
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO api_cache (cache_key, source, data_json, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        source = excluded.source,
                        data_json = excluded.data_json,
                        created_at = excluded.created_at
                """, (key, source, data_json, now))
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache write error for key {key}: {e}")

def clear_cache():
    """Clear all cached entries."""
    with _lock:
        _mem_cache.clear()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM api_cache")
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache clear error: {e}")
