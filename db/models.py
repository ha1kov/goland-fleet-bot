from __future__ import annotations

import sqlite3
from pathlib import Path

CREATE_VEHICLES_TABLE = """
CREATE TABLE IF NOT EXISTS vehicles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    plate            TEXT    NOT NULL UNIQUE,
    inspection_date  TEXT,
    adr              INTEGER NOT NULL DEFAULT 0,
    green_card_date  TEXT,
    insurance_date   TEXT,
    extract          TEXT,
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_PLATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles (plate);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        conn.execute(CREATE_VEHICLES_TABLE)
        conn.execute(CREATE_PLATE_INDEX)
        conn.commit()
