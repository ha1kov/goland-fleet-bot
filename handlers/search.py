from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from db.queries import get_vehicle_by_plate, search_vehicles_by_plate
from utils.formatters import search_result_line, vehicle_card

logger = logging.getLogger(__name__)

router = Router()

def _vehicle_action_keyboard(plate: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати дату ТО",
                    callback_data=f"edit:inspection:{plate}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати страховку",
                    callback_data=f"edit:insurance:{plate}",
                ),
                InlineKeyboardButton(
                    text="✏️ Редагувати Зелену карту",
                    callback_data=f"edit:green_card:{plate}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Оновити",
                    callback_data=f"view:{plate}",
                ),
            ],
        ]
    )


def _search_results_keyboard(vehicles) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=search_result_line(v),
                callback_data=f"view:{v['plate']}",
            )
        ]
        for v in vehicles
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("search"))
@router.message(F.text == "🔍 Знайти авто")
async def cmd_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🔍 Введіть номер авто або його частину:\n"
        "<i>Приклад: BH9800 або OO028</i>",
        parse_mode="HTML",
    )
    await state.set_state("waiting_for_search_query")


@router.message(F.text, F.text.func(lambda t: not t.startswith("/")))
async def handle_search_query(
    message: Message, state: FSMContext, db_path: Path
) -> None:
    current = await state.get_state()
    if current != "waiting_for_search_query":
        return

    query = message.text.strip()
    if len(query) < 2:
        await message.answer("⚠️ Введіть щонайменше 2 символи.")
        return

    vehicles = search_vehicles_by_plate(db_path, query)

    if not vehicles:
        await message.answer(
            f"❌ Авто за запитом <code>{query}</code> не знайдено.",
            parse_mode="HTML",
        )
        return

    await state.clear()

    if len(vehicles) == 1:
        await _send_vehicle_card(message, vehicles[0]["plate"], db_path)
        return

    kb = _search_results_keyboard(vehicles)
    await message.answer(
        f"🔍 Знайдено авто: <b>{len(vehicles)}</b>. Натисніть, щоб переглянути деталі:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("view:"))
async def cb_view_vehicle(callback: CallbackQuery, db_path: Path) -> None:
    plate = callback.data.split(":", 1)[1]
    await callback.answer()
    await _send_vehicle_card(callback.message, plate, db_path, edit=True)


async def _send_vehicle_card(
    target: Message,
    plate: str,
    db_path: Path,
    edit: bool = False,
) -> None:
    vehicle = get_vehicle_by_plate(db_path, plate)

    if not vehicle:
        await target.answer(f"❌ Авто <code>{plate}</code> не знайдено.", parse_mode="HTML")
        return

    text = vehicle_card(vehicle)
    kb = _vehicle_action_keyboard(plate)

    if edit:
        try:
            await target.edit_text(text, parse_mode="HTML", reply_markup=kb)
            return
        except Exception:
            pass

    await target.answer(text, parse_mode="HTML", reply_markup=kb)
