from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from db.queries import upsert_vehicle, get_vehicle_by_plate
from utils.formatters import vehicle_card

logger = logging.getLogger(__name__)

router = Router()

class AddVehicle(StatesGroup):
    waiting_for_plate = State()
    waiting_for_name = State()

@router.message(Command("add"))
@router.message(lambda m: m.text == "➕ Додати авто")
async def cmd_add_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddVehicle.waiting_for_plate)
    await message.answer(
        "➕ <b>Додавання нового авто</b>\n\n"
        "Введіть <b>номерний знак</b> авто (наприклад, <code>АА1234ВВ</code>):",
        parse_mode="HTML"
    )

@router.message(StateFilter(AddVehicle.waiting_for_plate))
async def process_add_plate(message: Message, state: FSMContext, db_path: Path) -> None:
    plate = message.text.strip().upper() if message.text else ""
    
    if not plate:
        await message.answer("⚠️ Будь ласка, введіть коректний номерний знак:")
        return

    existing = get_vehicle_by_plate(db_path, plate)
    if existing:
        await state.clear()
        
        from handlers.search import _vehicle_action_keyboard
        text = vehicle_card(existing)
        kb = _vehicle_action_keyboard(plate)
        
        await message.answer(
            f"⚠️ Авто з номером <b>{plate}</b> вже існує:\n\n{text}",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    await state.update_data(plate=plate)
    await state.set_state(AddVehicle.waiting_for_name)
    await message.answer(
        "Введіть <b>марку та модель</b> авто (наприклад, <code>MAN TGX</code>):",
        parse_mode="HTML"
    )

@router.message(StateFilter(AddVehicle.waiting_for_name))
async def process_add_name(message: Message, state: FSMContext, db_path: Path) -> None:
    name = message.text.strip() if message.text else ""
    
    if not name:
        await message.answer("⚠️ Будь ласка, введіть коректну назву авто:")
        return

    data = await state.get_data()
    plate = data["plate"]

    upsert_vehicle(
        db_path=db_path,
        name=name,
        plate=plate,
        inspection_date=None,
        adr=0,
        green_card_date=None,
        insurance_date=None,
        extract=None
    )
    
    await state.clear()
    
    vehicle = get_vehicle_by_plate(db_path, plate)
    if vehicle:
        from handlers.search import _vehicle_action_keyboard
        text = vehicle_card(vehicle)
        kb = _vehicle_action_keyboard(plate)
        
        await message.answer(
            f"✅ Авто <b>{plate}</b> успішно додано!\n\n{text}",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await message.answer("❌ Сталася помилка при додаванні авто.")
