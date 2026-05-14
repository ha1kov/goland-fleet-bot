from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from db.models import init_db
from db.queries import get_all_vehicles, upsert_vehicle

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "Name": "name",
    "Vehicle Number": "plate",
    "Inspection Start": "inspection_date",
    "ADR": "adr",
    "Green Card": "green_card_date",
    "Insurance": "insurance_date",
    "Extract": "extract",
}


def _to_date_str(value) -> str | None:
    if pd.isna(value):
        return None
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def import_xlsx(xlsx_path: Path, db_path: Path, force: bool = False) -> int:
    init_db(db_path)

    if not force and get_all_vehicles(db_path):
        logger.info("Database already populated — skipping XLSX import.")
        return 0

    if not xlsx_path.exists():
        raise FileNotFoundError(f"XLSX file not found: {xlsx_path}")

    logger.info("Importing vehicles from %s …", xlsx_path)

    df = pd.read_excel(xlsx_path, parse_dates=["Inspection Start", "Green Card", "Insurance"])

    df = df.rename(columns=COLUMN_MAP)

    df = df[df["plate"].notna() & (df["plate"].astype(str).str.strip() != "")]

    count = 0
    for _, row in df.iterrows():
        plate = str(row["plate"]).strip().upper()
        if not plate:
            continue

        upsert_vehicle(
            db_path=db_path,
            name=str(row.get("name", "")).strip(),
            plate=plate,
            inspection_date=_to_date_str(row.get("inspection_date")),
            adr=int(row.get("adr") == 1),
            green_card_date=_to_date_str(row.get("green_card_date")),
            insurance_date=_to_date_str(row.get("insurance_date")),
            extract=_to_date_str(row.get("extract")),
        )
        count += 1

    logger.info("Import complete — %d vehicles loaded.", count)
    return count


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    from config import settings

    imported = import_xlsx(settings.xlsx_path, settings.db_path, force=True)
    print(f"Imported {imported} vehicles.")
