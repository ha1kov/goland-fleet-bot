from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from db.queries import delete_vehicle_by_plate, get_vehicle_by_plate

logger = logging.getLogger(__name__)

router = Router()


def _delete_confirm_keyboard(plate: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, видалити",
                    callback_data=f"delete_yes:{plate}",
                ),
                InlineKeyboardButton(
                    text="❌ Ні, скасувати",
                    callback_data=f"view:{plate}",
                ),
            ]
        ]
    )


@router.callback_query(F.data.startswith("delete:"))
async def cb_delete_confirm(callback: CallbackQuery, db_path: Path) -> None:
    await callback.answer()
    
    parts = callback.data.split(":", 1)
    if len(parts) != 2:
        return
    plate = parts[1]

    vehicle = get_vehicle_by_plate(db_path, plate)
    if not vehicle:
        await callback.message.answer(f"❌ Авто <code>{plate}</code> не знайдено.", parse_mode="HTML")
        return

    await callback.message.edit_text(
        f"⚠️ Ви впевнені, що хочете видалити авто <b>{plate}</b>?",
        parse_mode="HTML",
        reply_markup=_delete_confirm_keyboard(plate),
    )


@router.callback_query(F.data.startswith("delete_yes:"))
async def cb_delete_yes(callback: CallbackQuery, db_path: Path) -> None:
    await callback.answer()
    
    parts = callback.data.split(":", 1)
    if len(parts) != 2:
        return
    plate = parts[1]

    success = delete_vehicle_by_plate(db_path, plate)
    if success:
        await callback.message.edit_text(f"✅ Авто <b>{plate}</b> успішно видалено.", parse_mode="HTML")
    else:
        await callback.message.edit_text(f"❌ Не вдалося видалити авто <b>{plate}</b>. Можливо, воно вже видалене.", parse_mode="HTML")
