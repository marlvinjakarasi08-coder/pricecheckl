"""
SQLite helpers for PriceCheck.

One table (`prices`) stores market rows from scrapes or sample fallbacks.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

import os
import sys

def _db_path():
    if sys.platform == "win32":
        folder = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PriceCheck"
    else:
        folder = Path(__file__).resolve().parent.parent
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "pricecheck.db"

DB_PATH = _db_path()

# Built-in aliases so typed search finds the right product.
ALIASES: dict[str, list[str]] = {
    "maize": ["maize", "corn", "mealie", "mealies"],
    "tomato": ["tomato", "tomatoes"],
    "potato": ["potato", "potatoes"],
    "soya": ["soya", "soya beans", "soyabeans", "soybean", "soybeans", "soy"],
    "sweet-potato": ["sweet potato", "sweet potatoes", "sweetpotato"],
    "onion-dried": ["onion", "onions", "dried onion", "dried onions"],
    "onion-fresh": ["fresh onion", "fresh onions"],
    "cabbage-white": ["cabbage", "cabbages", "white cabbage"],
    "carrot": ["carrot", "carrots"],
    "covo": ["covo", "kale"],
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create / migrate the prices table."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commodity TEXT NOT NULL,
                display_name TEXT,
                market TEXT NOT NULL,
                min_price REAL,
                max_price REAL,
                unit TEXT,
                currency TEXT,
                source TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Lightweight migration for DBs created before display_name existed
        cols = {row[1] for row in conn.execute("PRAGMA table_info(prices)")}
        if "display_name" not in cols:
            conn.execute("ALTER TABLE prices ADD COLUMN display_name TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prices_commodity ON prices(commodity)"
        )
        conn.commit()


def clear_and_insert_prices(rows: Iterable[dict[str, Any]]) -> int:
    rows = list(rows)
    with get_connection() as conn:
        conn.execute("DELETE FROM prices")
        conn.executemany(
            """
            INSERT INTO prices (
                commodity, display_name, market, min_price, max_price,
                unit, currency, source, updated_at
            ) VALUES (
                :commodity, :display_name, :market, :min_price, :max_price,
                :unit, :currency, :source, :updated_at
            )
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def count_prices() -> int:
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) AS n FROM prices")
        return int(cur.fetchone()["n"])


def list_commodities(q: Optional[str] = None) -> list[dict[str, str]]:
    """
    Distinct products in the DB, optionally filtered by typed search.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT commodity AS id,
                   COALESCE(NULLIF(display_name, ''), commodity) AS name
            FROM prices
            GROUP BY commodity
            ORDER BY name COLLATE NOCASE
            """
        )
        items = [{"id": row["id"], "name": row["name"]} for row in cur.fetchall()]

    if not q:
        return items

    needle = q.strip().lower()
    if not needle:
        return items

    matched = []
    for item in items:
        hay = f"{item['id']} {item['name']}".lower()
        alias_hit = any(
            needle in a or a in needle
            for a in ALIASES.get(item["id"], [])
        )
        if needle in hay or alias_hit:
            matched.append(item)
    return matched


def resolve_commodity(raw: Optional[str]) -> Optional[str]:
    """
    Map a typed query / id / alias to a commodity id present in the DB.
    Prefers exact id, then alias, then unique substring match on name.
    """
    if not raw:
        return None
    key = raw.strip().lower()
    if not key:
        return None

    items = list_commodities()
    by_id = {i["id"].lower(): i["id"] for i in items}
    if key in by_id:
        return by_id[key]

    for cid, aliases in ALIASES.items():
        if key in aliases and cid in by_id:
            return cid

    # Unique name / id substring
    hits = [
        i["id"]
        for i in items
        if key in i["id"].lower() or key in i["name"].lower()
    ]
    if len(hits) == 1:
        return hits[0]

    # Alias substring unique
    alias_hits = []
    for cid, aliases in ALIASES.items():
        if cid in by_id and any(key in a or a in key for a in aliases):
            alias_hits.append(cid)
    alias_hits = list(dict.fromkeys(alias_hits))
    if len(alias_hits) == 1:
        return alias_hits[0]

    return None


def get_prices(
    commodity: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Fetch price rows; filter by commodity id or free-text search."""
    cid = None
    if commodity:
        cid = resolve_commodity(commodity)
    elif q:
        cid = resolve_commodity(q)

    with get_connection() as conn:
        if cid:
            cur = conn.execute(
                """
                SELECT commodity, display_name, market, min_price, max_price,
                       unit, currency, source, updated_at
                FROM prices
                WHERE commodity = ?
                ORDER BY market
                """,
                (cid,),
            )
        elif q:
            # Broad search across names when resolve was ambiguous
            like = f"%{q.strip()}%"
            cur = conn.execute(
                """
                SELECT commodity, display_name, market, min_price, max_price,
                       unit, currency, source, updated_at
                FROM prices
                WHERE commodity LIKE ? COLLATE NOCASE
                   OR display_name LIKE ? COLLATE NOCASE
                ORDER BY display_name, market
                """,
                (like, like),
            )
        else:
            cur = conn.execute(
                """
                SELECT commodity, display_name, market, min_price, max_price,
                       unit, currency, source, updated_at
                FROM prices
                ORDER BY display_name, market
                """
            )
        return [dict(row) for row in cur.fetchall()]
