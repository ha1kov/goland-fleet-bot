from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from db.models import get_connection


Vehicle = sqlite3.Row

def get_vehicle_by_plate(db_path: Path, plate: str) -> Optional[Vehicle]:
    plate = plate.strip().upper()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM vehicles WHERE plate = ?", (plate,)
        ).fetchone()
    return row


def search_vehicles_by_plate(db_path: Path, query: str) -> list[Vehicle]:
    pattern = f"%{query.strip().upper()}%"
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM vehicles WHERE plate LIKE ? ORDER BY plate LIMIT 10",
            (pattern,),
        ).fetchall()
    return rows


def get_expiring_vehicles(db_path: Path, warn_days: int = 7) -> list[Vehicle]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM   vehicles
            WHERE  inspection_date IS NOT NULL
              AND  (
                (adr = 1 AND (
                  date(inspection_date, '+6 months') = date('now', '+7 days')
                  OR date(inspection_date, '+6 months') = date('now', '+3 days')
                  OR date(inspection_date, '+6 months') = date('now', '+1 days')
                  OR date(inspection_date, '+6 months') <= date('now')
                ))
                OR
                (adr = 0 AND (
                  date(inspection_date, '+12 months') = date('now', '+7 days')
                  OR date(inspection_date, '+12 months') = date('now', '+3 days')
                  OR date(inspection_date, '+12 months') = date('now', '+1 days')
                  OR date(inspection_date, '+12 months') <= date('now')
                ))
              )
            ORDER  BY inspection_date
            """
        ).fetchall()
    return rows

def get_all_vehicles(db_path: Path) -> list[Vehicle]:
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM vehicles ORDER BY plate"
        ).fetchall()

def upsert_vehicle(
    db_path: Path,
    name: str,
    plate: str,
    inspection_date: Optional[str],
    adr: int,
    green_card_date: Optional[str],
    insurance_date: Optional[str],
    extract: Optional[str],
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO vehicles
                (name, plate, inspection_date, adr, green_card_date, insurance_date, extract)
            VALUES (:name, :plate, :inspection_date, :adr, :green_card_date, :insurance_date, :extract)
            ON CONFLICT(plate) DO UPDATE SET
                name             = excluded.name,
                inspection_date  = excluded.inspection_date,
                adr              = excluded.adr,
                green_card_date  = excluded.green_card_date,
                insurance_date   = excluded.insurance_date,
                extract          = excluded.extract,
                updated_at       = datetime('now')
            """,
            {
                "name": name,
                "plate": plate,
                "inspection_date": inspection_date,
                "adr": adr,
                "green_card_date": green_card_date,
                "insurance_date": insurance_date,
                "extract": extract,
            },
        )
        conn.commit()


def update_inspection_date(db_path: Path, plate: str, date_str: str) -> bool:
    return _update_date_field(db_path, plate, "inspection_date", date_str)


def update_insurance_date(db_path: Path, plate: str, date_str: str) -> bool:
    return _update_date_field(db_path, plate, "insurance_date", date_str)


def update_green_card_date(db_path: Path, plate: str, date_str: str) -> bool:
    return _update_date_field(db_path, plate, "green_card_date", date_str)

def _update_date_field(db_path: Path, plate: str, field: str, date_str: str) -> bool:
    allowed = {"inspection_date", "insurance_date", "green_card_date"}
    if field not in allowed:
        raise ValueError(f"Unknown field: {field}")

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE vehicles SET {field} = ?, updated_at = datetime('now') WHERE plate = ?",
            (date_str, plate.upper()),
        )
        conn.commit()
        return cursor.rowcount > 0
