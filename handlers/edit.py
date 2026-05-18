from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from db.queries import (
    get_vehicle_by_plate,
    update_green_card_date,
    update_inspection_date,
    update_insurance_date,
)
from utils.formatters import vehicle_card

logger = logging.getLogger(__name__)

router = Router()

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

class EditDate(StatesGroup):
    waiting_for_date = State()


FIELD_META = {
    "inspection": {
        "label": "ТО (техогляд)",
        "updater": update_inspection_date,
    },
    "insurance": {
        "label": "Страховка",
        "updater": update_insurance_date,
    },
    "green_card": {
        "label": "Зелена карта",
        "updater": update_green_card_date,
    },
}


def _cancel_keyboard(plate: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data=f"edit_cancel:{plate}",
                )
            ]
        ]
    )


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit_start(
    callback: CallbackQuery, state: FSMContext, db_path: Path
) -> None:
    await callback.answer()

    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.message.answer("⚠️ Некоректний запит на редагування.")
        return

    _, field, plate = parts
    plate = plate.upper()

    if field not in FIELD_META:
        await callback.message.answer("⚠️ Невідоме поле.")
        return

    vehicle = get_vehicle_by_plate(db_path, plate)
    if not vehicle:
        await callback.message.answer(f"❌ Авто <code>{plate}</code> не знайдено.", parse_mode="HTML")
        return

    label = FIELD_META[field]["label"]

    await state.set_state(EditDate.waiting_for_date)
    await state.update_data(plate=plate, field=field)

    from utils.state import chat_alert_messages
    chat_id = callback.message.chat.id
    if chat_id in chat_alert_messages and callback.message.message_id in chat_alert_messages[chat_id]:
        for msg_id in chat_alert_messages[chat_id]:
            try:
                await callback.bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        chat_alert_messages.pop(chat_id, None)

    msg = await callback.message.answer(
        f"✏️ Редагування поля <b>{label}</b> для авто <code>{plate}</code>\n\n"
        f"Надішліть нову дату у форматі <code>YYYY-MM-DD</code>\n"
        f"<i>Приклад: 2026-06-15</i>",
        parse_mode="HTML",
        reply_markup=_cancel_keyboard(plate),
    )
    await state.update_data(prompt_msg_id=msg.message_id)


@router.callback_query(F.data.startswith("edit_cancel:"))
async def cb_edit_cancel(
    callback: CallbackQuery, state: FSMContext, db_path: Path
) -> None:
    await callback.answer("Скасовано.")
    await state.clear()

    plate = callback.data.split(":", 1)[1]
    vehicle = get_vehicle_by_plate(db_path, plate)

    if vehicle:
        from handlers.search import _vehicle_action_keyboard

        text = vehicle_card(vehicle)
        kb = _vehicle_action_keyboard(plate)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer("Редагування скасовано.")


@router.message(StateFilter(EditDate.waiting_for_date))
async def handle_new_date(
    message: Message, state: FSMContext, db_path: Path
) -> None:
    data = await state.get_data()
    plate: str = data["plate"]
    field: str = data["field"]

    raw = message.text.strip() if message.text else ""

    if not DATE_RE.match(raw):
        await message.answer(
            "⚠️ Некоректний формат. Використовуйте <code>YYYY-MM-DD</code>\n"
            "<i>Приклад: 2026-06-15</i>",
            parse_mode="HTML",
        )
        return

    try:
        datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            "⚠️ Такої дати не існує (наприклад, 30 лютого).\n"
            "Спробуйте ще раз із коректною датою у форматі <code>YYYY-MM-DD</code>.",
            parse_mode="HTML",
        )
        return

    meta = FIELD_META[field]
    updater = meta["updater"]
    label = meta["label"]

    success = updater(db_path, plate, raw)

    if not success:
        await message.answer(
            f"❌ Не вдалося оновити дані — авто <code>{plate}</code> не знайдено.",
            parse_mode="HTML",
        )
        await state.clear()
        return

    prompt_msg_id = data.get("prompt_msg_id")
    await state.clear()

    try:
        if prompt_msg_id:
            await message.bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()
    except Exception:
        pass

    logger.info("Updated %s for %s → %s", field, plate, raw)

    vehicle = get_vehicle_by_plate(db_path, plate)

    from handlers.search import _vehicle_action_keyboard

    success_text = (
        f"✅ <b>{label}</b> оновлено на <code>{raw}</code> для <code>{plate}</code>\n\n"
    )
    card_text = vehicle_card(vehicle) if vehicle else ""
    kb = _vehicle_action_keyboard(plate) if vehicle else None

    await message.answer(
        success_text + card_text,
        parse_mode="HTML",
        reply_markup=kb,
    )
