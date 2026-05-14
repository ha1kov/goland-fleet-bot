from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: _require("BOT_TOKEN"))
    admin_chat_id: int = field(default_factory=lambda: int(_require("ADMIN_CHAT_ID")))
    xlsx_path: Path = field(default_factory=lambda: Path(os.getenv("XLSX_PATH", "cars.xlsx")))
    db_path: Path = field(default_factory=lambda: Path(os.getenv("DB_PATH", "fleet.db")))
    notify_hour: int = field(default_factory=lambda: int(os.getenv("NOTIFY_HOUR", "8")))
    notify_minute: int = field(default_factory=lambda: int(os.getenv("NOTIFY_MINUTE", "0")))
    to_warn_days: int = field(default_factory=lambda: int(os.getenv("TO_WARN_DAYS", "7")))


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example → .env and fill in the values."
        )
    return value


settings = Settings()
