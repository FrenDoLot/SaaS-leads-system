from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from app.config import load_config
from app.database import (
    get_owner_by_tg_user_id,
    get_subscription_by_owner_id,
    has_active_access_by_owner_id,
    get_all_leads,
    get_leads_stats,
    get_unique_clients,
)
from app.keyboards.main_menu import (
    active_owner_menu,
    expired_owner_menu,
    tariffs_menu,
)


router = Router()


ADMIN_CONTACT = "@FrenDoLot"


def build_owner_link(bot_username: str, owner_id: int) -> str:
    return f"https://t.me/{bot_username}?start=owner_{owner_id}"


def get_status_text(status: str) -> str:
    if status == "trial":
        return "пробный период"

    if status == "active":
        return "активная подписка"

    if status == "expired":
        return "доступ закончился"

    return status


def get_plan_text(plan: str) -> str:
    if plan == "trial":
        return "3 дня бесплатно"

    if plan == "month":
        return "399 ₽ / месяц"

    if plan == "year":
        return "2999 ₽ / год"

    if plan == "manual":
        return "активировано вручную"

    return plan


async def get_current_owner(message: Message):
    owner = await get_owner_by_tg_user_id(message.from_user.id)

    if not owner:
        await message.answer(
            "Вы ещё не зарегистрированы как владелец.\n\n"
            "Нажмите /start, чтобы начать."
        )
        return None

    return owner


async def access_expired_message(message: Message):
    await message.answer(
        "⛔ Пробный период закончился, вы можете приобрести подписку "
        "в разделе «Приобрести подписку!».\n\n"
        f"Для подключения подписки напишите администратору: {ADMIN_CONTACT}",
        reply_markup=expired_owner_menu(),
    )


@router.message(F.text == "🔗 Моя ссылка")
async def show_personal_link(message: Message):
    owner = await get_current_owner(message)

    if not owner:
        return

    owner_id = owner[0]

    has_access = await has_active_access_by_owner_id(owner_id)

    if not has_access:
        await access_expired_message(message)
        return

    config = load_config()
    link = build_owner_link(config.bot_username, owner_id)

    await message.answer(
        "🔗 Ваша персональная ссылка для приёма заявок:\n\n"
        f"{link}\n\n"
        "Отправьте эту ссылку своим клиентам.\n"
        "Клиент перейдёт по ссылке, заполнит анкету, "
        "и заявка сразу придёт вам в Telegram.",
        reply_markup=active_owner_menu(),
    )


@router.message(F.text == "📥 Мои заявки")
async def show_leads(message: Message):
    owner = await get_current_owner(message)

    if not owner:
        return

    owner_id = owner[0]

    has_access = await has_active_access_by_owner_id(owner_id)

    if not has_access:
        await access_expired_message(message)
        return

    leads = await get_all_leads(owner_id=owner_id, limit=10)

    if not leads:
        await message.answer("📥 Заявок пока нет.")
        return

    text = "📥 Последние заявки:\n\n"

    for index, (name, contact, comment, created_at) in enumerate(leads, start=1):
        try:
            created_at_dt = datetime.fromisoformat(created_at)
            created_at_text = created_at_dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            created_at_text = created_at

        text += (
            f"{index}. 👤 {name}\n"
            f"📞 Контакт: {contact}\n"
            f"💬 Комментарий: {comment}\n"
            f"🕒 {created_at_text}\n\n"
        )

    await message.answer(text[:4000])


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    owner = await get_current_owner(message)

    if not owner:
        return

    owner_id = owner[0]

    has_access = await has_active_access_by_owner_id(owner_id)

    if not has_access:
        await access_expired_message(message)
        return

    stats = await get_leads_stats(owner_id=owner_id)

    await message.answer(
        "📊 Статистика заявок\n\n"
        f"📅 Сегодня: {stats['today']}\n"
        f"📆 За 7 дней: {stats['week']}\n"
        f"📦 Всего: {stats['total']}",
        reply_markup=active_owner_menu(),
    )


@router.message(F.text == "👥 Клиенты")
async def show_clients(message: Message):
    owner = await get_current_owner(message)

    if not owner:
        return

    owner_id = owner[0]

    has_access = await has_active_access_by_owner_id(owner_id)

    if not has_access:
        await access_expired_message(message)
        return

    clients = await get_unique_clients(owner_id=owner_id)

    if not clients:
        await message.answer("👥 Клиентов пока нет.")
        return

    text = "👥 База клиентов\n\n"

    for index, (name, contact, leads_count) in enumerate(clients, start=1):
        text += (
            f"{index}. 👤 {name}\n"
            f"📞 Контакт: {contact}\n"
            f"📝 Заявок: {leads_count}\n\n"
        )

    await message.answer(text[:4000])


@router.message(F.text == "💳 Подписка")
async def show_subscription(message: Message):
    owner = await get_current_owner(message)

    if not owner:
        return

    owner_id = owner[0]

    subscription = await get_subscription_by_owner_id(owner_id)

    if not subscription:
        await message.answer(
            "💳 Подписка\n\n"
            "У вас пока нет активного пробного периода или подписки.\n\n"
            "Вы можете активировать пробный период на 3 дня "
            "или приобрести подписку.\n\n"
            "Тарифы:\n"
            "💳 399 ₽ / месяц\n"
            "🔥 2999 ₽ / год\n\n"
            f"Для подключения подписки напишите администратору: {ADMIN_CONTACT}",
            reply_markup=tariffs_menu(),
        )
        return

    status, plan, started_at, paid_until = subscription

    status_text = get_status_text(status)
    plan_text = get_plan_text(plan)

    try:
        paid_until_dt = datetime.fromisoformat(paid_until)
        paid_until_text = paid_until_dt.strftime("%d.%m.%Y %H:%M")
        days_left = (paid_until_dt - datetime.now()).days

        if days_left < 0:
            days_left = 0
    except Exception:
        paid_until_text = paid_until
        days_left = 0

    has_access = await has_active_access_by_owner_id(owner_id)

    if not has_access:
        await message.answer(
            "💳 Подписка\n\n"
            "⛔ Пробный период закончился.\n\n"
            "Вы можете приобрести подписку в разделе "
            "«Приобрести подписку!».\n\n"
            "Тарифы:\n"
            "💳 399 ₽ / месяц\n"
            "🔥 2999 ₽ / год\n\n"
            f"Для подключения подписки напишите администратору: {ADMIN_CONTACT}",
            reply_markup=expired_owner_menu(),
        )
        return

    await message.answer(
        "💳 Подписка\n\n"
        "✅ Доступ активен\n"
        f"📌 Статус: {status_text}\n"
        f"📦 Тариф: {plan_text}\n"
        f"⏳ Осталось дней: {days_left}\n"
        f"📅 Доступ до: {paid_until_text}\n\n"
        "Тарифы:\n"
        "💳 399 ₽ / месяц\n"
        "🔥 2999 ₽ / год\n\n"
        f"Если хотите приобрести полноценную подписку — обращайтесь к {ADMIN_CONTACT}",
        reply_markup=active_owner_menu(),
    )