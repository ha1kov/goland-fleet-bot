from __future__ import annotations

import sqlite3
import calendar
from datetime import date, datetime


def _fmt_date(value: str | None) -> str:
    if not value:
        return "—"
    return value


def _adr_emoji(adr: int) -> str:
    return "✅ Так" if adr else "❌ Ні"


def _calc_to_expiry(date_str: str | None, adr: int) -> date | None:
    if not date_str:
        return None
    try:
        start = datetime.strptime(date_str, "%Y-%m-%d").date()
        months = 6 if adr else 12
        
        month = start.month - 1 + months
        year = start.year + month // 12
        month = month % 12 + 1
        day = start.day
        
        try:
            return date(year, month, day)
        except ValueError:
            return date(year, month, calendar.monthrange(year, month)[1])
    except Exception:
        return None


def _days_delta_from_expiry(expiry: date | None) -> str:
    if not expiry:
        return ""
    delta = (expiry - date.today()).days
    if delta < 0:
        return f"⛔ ПРОСТРОЧЕНО на {abs(delta)} дн."
    elif delta == 0:
        return "⚠️ Закінчується сьогодні"
    else:
        return f"⏳ Залишилося {delta} дн."


def vehicle_card(v: sqlite3.Row) -> str:
    to_expiry = _calc_to_expiry(v["inspection_date"], v["adr"])
    to_status = _days_delta_from_expiry(to_expiry)
    
    to_line = f"{_fmt_date(v['inspection_date'])}"
    if to_expiry:
        to_line += f" (до {to_expiry.strftime('%Y-%m-%d')})"
    if to_status:
        to_line += f"  {to_status}"

    return (
        f"🚛 <b>{v['name']}</b>\n"
        f"🔖 Номер: <code>{v['plate']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔧 ТО (техогляд): {to_line}\n"
        f"🔰 ADR: {_adr_emoji(v['adr'])}\n"
        f"🟢 Зелена карта: {_fmt_date(v['green_card_date'])}\n"
        f"🛡 Страховка: {_fmt_date(v['insurance_date'])}\n"
    )


def notification_message(v: sqlite3.Row) -> str:
    to_expiry = _calc_to_expiry(v["inspection_date"], v["adr"])
    to_status = _days_delta_from_expiry(to_expiry)
    
    to_line = f"{_fmt_date(v['inspection_date'])}"
    if to_expiry:
        to_line += f" (до {to_expiry.strftime('%Y-%m-%d')})"

    return (
        f"🚨 <b>Сповіщення про техогляд автопарку</b>\n\n"
        f"🚛 <b>{v['name']}</b>\n"
        f"🔖 Номер: <code>{v['plate']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔧 ТО: {to_line}\n"
        f"   {to_status}\n"
        f"🔰 ADR: {_adr_emoji(v['adr'])}\n"
        f"🟢 Зелена карта: {_fmt_date(v['green_card_date'])}\n"
        f"🛡 Страховка: {_fmt_date(v['insurance_date'])}\n"
    )


def search_result_line(v: sqlite3.Row) -> str:
    to_expiry = _calc_to_expiry(v["inspection_date"], v["adr"])
    to = to_expiry.strftime('%Y-%m-%d') if to_expiry else _fmt_date(v["inspection_date"])
    return f"{v['plate']}  |  {v['name'][:28]}  |  ТО до: {to}"
