from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db.queries import get_expiring_vehicles
from utils.formatters import notification_message

logger = logging.getLogger(__name__)

def _check_expiring_vehicles(
    bot,
    admin_chat_id: int,
    db_path: Path,
    warn_days: int,
    loop: asyncio.AbstractEventLoop,
) -> None:
    logger.info("Running daily inspection check…")

    vehicles = get_expiring_vehicles(db_path, warn_days)

    if not vehicles:
        logger.info("No vehicles require attention today.")
        return

    logger.info("%d vehicle(s) require attention.", len(vehicles))

    async def _send_all() -> None:
        from utils.state import chat_alert_messages
        from handlers.search import _vehicle_action_keyboard

        header = (
            f"📋 <b>Щоденний звіт автопарку</b>  —  "
            f"потребують уваги: <b>{len(vehicles)}</b>\n"
        )
        msg1 = await bot.send_message(admin_chat_id, header, parse_mode="HTML")
        msg_ids = [msg1.message_id]

        for v in vehicles:
            text = notification_message(v)
            kb = _vehicle_action_keyboard(v["plate"])
            msg = await bot.send_message(admin_chat_id, text, parse_mode="HTML", reply_markup=kb)
            msg_ids.append(msg.message_id)

        chat_alert_messages[admin_chat_id] = msg_ids

    future = asyncio.run_coroutine_threadsafe(_send_all(), loop)
    try:
        future.result(timeout=30)
    except Exception as exc:
        logger.error("Failed to send notifications: %s", exc)


def build_scheduler(
    bot,
    admin_chat_id: int,
    db_path: Path,
    warn_days: int,
    notify_hour: int,
    notify_minute: int,
    loop: asyncio.AbstractEventLoop,
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        func=_check_expiring_vehicles,
        trigger=CronTrigger(hour=notify_hour, minute=notify_minute, timezone="UTC"),
        kwargs={
            "bot": bot,
            "admin_chat_id": admin_chat_id,
            "db_path": db_path,
            "warn_days": warn_days,
            "loop": loop,
        },
        id="daily_inspection_check",
        name="Daily TO inspection alert",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "Scheduler configured — daily check at %02d:%02d UTC.", notify_hour, notify_minute
    )
    return scheduler
