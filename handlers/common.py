from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import settings
from db.queries import get_expiring_vehicles
from utils.formatters import notification_message

router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Знайти авто")],
        [KeyboardButton(text="➕ Додати авто")],
        [KeyboardButton(text="⏰ Перевірити ТО")],
        [KeyboardButton(text="📋 Допомога")],
    ],
    resize_keyboard=True,
)

HELP_TEXT = (
    "🚛 <b>Бот керування автопарком</b>\n\n"
    "Доступні команди:\n"
    "• /start — показати головне меню\n"
    "• /help — показати допомогу\n"
    "• /search — знайти авто за номером\n"
    "• /add — додати нове авто\n\n"
    "• /alerts — перевірити прострочені або близькі до завершення ТО\n\n"
    "<b>Як користуватися:</b>\n"
    "1️⃣  Натисніть <b>🔍 Знайти авто</b> або введіть <code>/search НОМЕР</code>\n"
    "2️⃣  Оберіть авто з результатів\n"
    "3️⃣  Натисніть кнопку <b>✏️ Редагувати</b>, щоб оновити дату ТО, страховки або Зеленої карти\n"
    "4️⃣  Надішліть нову дату у форматі <code>YYYY-MM-DD</code>\n"
    "5️⃣  Натисніть <b>⏰ Перевірити ТО</b>, щоб вручну перевірити сповіщення\n\n"
    "🔔 Бот щодня надсилає сповіщення про авто, у яких техогляд (ТО) "
    "закінчується протягом 7 днів або вже прострочений."
)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Вітаю у <b>GOLAND Fleet Manager</b>!\n\n"
        "Скористайтеся меню нижче, щоб знайти авто або перевірити ТО.",
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("help"))
@router.message(lambda m: m.text == "📋 Допомога")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("alerts"))
@router.message(lambda m: m.text == "⏰ Перевірити ТО")
async def cmd_alerts(message: Message, db_path) -> None:
    vehicles = get_expiring_vehicles(db_path, settings.to_warn_days)

    if not vehicles:
        await message.answer(
            "✅ Немає авто з простроченим ТО або ТО, що скоро закінчується.",
            parse_mode="HTML",
        )
        return

    msg1 = await message.answer(
        f"📋 <b>Перевірка ТО</b>\n"
        f"Потребують уваги: <b>{len(vehicles)}</b>\n"
        f"Період попередження: <b>{settings.to_warn_days}</b> дн.",
        parse_mode="HTML",
    )

    from utils.state import chat_alert_messages
    from handlers.search import _vehicle_action_keyboard
    
    msg_ids = [message.message_id, msg1.message_id]

    for vehicle in vehicles:
        kb = _vehicle_action_keyboard(vehicle["plate"])
        msg = await message.answer(notification_message(vehicle), parse_mode="HTML", reply_markup=kb)
        msg_ids.append(msg.message_id)

    chat_alert_messages[message.chat.id] = msg_ids
