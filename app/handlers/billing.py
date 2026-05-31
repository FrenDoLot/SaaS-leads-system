from aiogram import Router, F
from aiogram.types import Message

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


def build_owner_link(bot_username: str, owner_id: int) -> str:
    return f"https://t.me/{bot_username}?start=owner_{owner_id}"


async def get_current_owner_id(message: Message) -> int:
    owner_id = await get_or_create_owner(
        tg_user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    return owner_id


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

    payment_id = await create_payment(
        owner_id=owner_id,
        amount=MONTH_PRICE,
        plan="month",
    )

    await message.answer(
        "💳 Тариф: 399 ₽ / месяц\n\n"
        "Оплата будет подключена следующим шагом.\n\n"
        f"ID платежа: {payment_id}\n\n"
        "Пока для теста админ может продлить доступ командой:\n"
        f"/extend {message.from_user.id} 30"
    )


@router.message(F.text == "🔥 2999 ₽ / год")
async def year_tariff_handler(message: Message):
    owner_id = await get_current_owner_id(message)

    payment_id = await create_payment(
        owner_id=owner_id,
        amount=YEAR_PRICE,
        plan="year",
    )

    await message.answer(
        "🔥 Тариф: 2999 ₽ / год\n\n"
        "Оплата будет подключена следующим шагом.\n\n"
        f"ID платежа: {payment_id}\n\n"
        "Пока для теста админ может продлить доступ командой:\n"
        f"/extend {message.from_user.id} 365"
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