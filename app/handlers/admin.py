from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from app.config import load_config
from app.database import extend_subscription


router = Router()


@router.message(Command("extend"))
async def extend_command(message: Message):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Использование:\n"
            "/extend <telegram_id> <days>\n\n"
            "Пример:\n"
            "/extend 123456789 30"
        )
        return

    try:
        tg_user_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("Telegram ID и количество дней должны быть числами.")
        return

    if days <= 0:
        await message.answer("Количество дней должно быть больше 0.")
        return

    result = await extend_subscription(tg_user_id=tg_user_id, days=days)

    if not result:
        await message.answer(
            "⛔ Владелец с таким Telegram ID не найден.\n\n"
            "Пусть пользователь сначала нажмёт /start в боте."
        )
        return

    await message.answer(
        f"✅ Подписка пользователя {tg_user_id} продлена на {days} дней."
    )