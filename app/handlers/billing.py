from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import load_config
from app.database import (
    get_or_create_owner,
    get_owner_by_tg_user_id,
    activate_trial,
    get_subscription_by_owner_id,
    create_payment,
    has_active_access_by_owner_id,
)
from app.keyboards.main_menu import (
    start_owner_menu,
    active_owner_menu,
    expired_owner_menu,
    tariffs_menu,
)


router = Router()


MONTH_PRICE = 399
YEAR_PRICE = 2999

ADMIN_USERNAME = "FrenDoLot"


def build_owner_link(bot_username: str, owner_id: int) -> str:
    return f"https://t.me/{bot_username}?start=owner_{owner_id}"


def contact_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📩 Написать администратору",
                    url=f"https://t.me/{ADMIN_USERNAME}",
                )
            ]
        ]
    )


async def get_current_owner_id(message: Message) -> int:
    owner_id = await get_or_create_owner(
        tg_user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    return owner_id


async def notify_admins_about_payment_request(
    message: Message,
    plan_text: str,
    days: int,
):
    config = load_config()

    username = message.from_user.username

    if username:
        username_text = f"@{username}"
    else:
        username_text = "не указан"

    text = (
        "💳 Новая заявка на подключение подписки!\n\n"
        f"📦 Тариф: {plan_text}\n"
        f"⏳ Дней доступа после оплаты: {days}\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n"
        f"📨 Username: {username_text}\n\n"
        "После оплаты продлите доступ командой:\n"
        f"/extend {message.from_user.id} {days}"
    )

    for admin_id in config.admin_ids:
        try:
            await message.bot.send_message(admin_id, text)
        except Exception:
            pass


@router.message(F.text == "🎁 Пробный период 3 дня")
async def activate_trial_handler(message: Message):
    owner_id = await get_current_owner_id(message)

    has_access = await has_active_access_by_owner_id(owner_id)

    if has_access:
        config = load_config()
        link = build_owner_link(config.bot_username, owner_id)

        await message.answer(
            "✅ У вас уже есть активный доступ.\n\n"
            "Ваша персональная ссылка для заявок:\n\n"
            f"{link}",
            reply_markup=active_owner_menu(),
        )
        return

    activated = await activate_trial(owner_id)

    if not activated:
        await message.answer(
            "⛔ Пробный период уже был активирован ранее.\n\n"
            "Вы можете приобрести подписку в разделе «Приобрести подписку!».",
            reply_markup=expired_owner_menu(),
        )
        return

    config = load_config()
    link = build_owner_link(config.bot_username, owner_id)

    await message.answer(
        "🎁 Пробный период активирован на 3 дня!\n\n"
        "Теперь вы можете принимать заявки от клиентов.\n\n"
        "Ваша персональная ссылка:\n\n"
        f"{link}\n\n"
        "Отправьте эту ссылку своим клиентам.",
        reply_markup=active_owner_menu(),
    )


@router.message(F.text == "💳 Приобрести подписку")
async def buy_subscription_handler(message: Message):
    await get_current_owner_id(message)

    await message.answer(
        "💳 Выберите тариф:\n\n"
        "💳 399 ₽ / месяц\n"
        "🔥 2999 ₽ / год",
        reply_markup=tariffs_menu(),
    )


@router.message(F.text == "💳 399 ₽ / месяц")
async def month_tariff_handler(message: Message):
    owner_id = await get_current_owner_id(message)

    await create_payment(
        owner_id=owner_id,
        amount=MONTH_PRICE,
        plan="month",
    )

    await notify_admins_about_payment_request(
        message=message,
        plan_text="399 ₽ / месяц",
        days=30,
    )

    await message.answer(
        "💳 Тариф: 399 ₽ / месяц\n\n"
        "Для подключения подписки напишите администратору.\n"
        "Он подскажет способ оплаты и активирует доступ после подтверждения.\n\n"
        "После оплаты сразу отправьте чек администратору — так доступ будет активирован быстрее.\n\n"
        "После активации вы снова сможете получить свою ссылку и принимать заявки.",
        reply_markup=contact_admin_keyboard(),
    )


@router.message(F.text == "🔥 2999 ₽ / год")
async def year_tariff_handler(message: Message):
    owner_id = await get_current_owner_id(message)

    await create_payment(
        owner_id=owner_id,
        amount=YEAR_PRICE,
        plan="year",
    )

    await notify_admins_about_payment_request(
        message=message,
        plan_text="2999 ₽ / год",
        days=365,
    )

    await message.answer(
        "🔥 Тариф: 2999 ₽ / год\n\n"
        "Для подключения подписки напишите администратору.\n"
        "Он подскажет способ оплаты и активирует доступ после подтверждения.\n\n"
        "После оплаты сразу отправьте чек администратору — так доступ будет активирован быстрее.\n\n"
        "После активации вы снова сможете получить свою ссылку и принимать заявки.",
        reply_markup=contact_admin_keyboard(),
    )


@router.message(F.text == "⬅️ Назад")
async def back_handler(message: Message):
    owner = await get_owner_by_tg_user_id(message.from_user.id)

    if not owner:
        await message.answer(
            "Вы можете активировать пробный период или приобрести подписку.",
            reply_markup=start_owner_menu(),
        )
        return

    owner_id = owner[0]
    subscription = await get_subscription_by_owner_id(owner_id)

    if not subscription:
        await message.answer(
            "Вы можете активировать пробный период или приобрести подписку.",
            reply_markup=start_owner_menu(),
        )
        return

    has_access = await has_active_access_by_owner_id(owner_id)

    if has_access:
        await message.answer(
            "Главное меню владельца.",
            reply_markup=active_owner_menu(),
        )
    else:
        await message.answer(
            "Пробный период закончился.\n\n"
            "Вы можете приобрести подписку в разделе «Приобрести подписку!».",
            reply_markup=expired_owner_menu(),
        )