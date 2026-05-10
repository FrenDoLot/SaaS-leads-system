from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.states.onboarding import LeadForm
from app.config import load_config
from app.keyboards.main_menu import client_menu
from app.database import (
    save_lead,
    get_all_leads,
    get_leads_stats,
    get_unique_clients,
    get_subscription,
    has_active_access,
)


router = Router()


async def access_denied(message: Message):
    await message.answer(
        "⛔ Доступ к сервису закончился.\n\n"
        "Чтобы продолжить пользоваться LeadNotifyBot, продлите подписку:\n"
        "💰 2 990 ₽ / месяц\n\n"
        "Нажмите 💳 Подписка для подробностей."
    )


@router.message(F.text == "📝 Оставить заявку")
async def start_lead_form(message: Message, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("owner_id")

    if owner_id is None:
        config = load_config()

        if message.from_user.id in config.admin_ids:
            owner_id = message.from_user.id
        else:
            await message.answer(
                "Чтобы оставить заявку, откройте персональную ссылку специалиста."
            )
            return

    if not await has_active_access(owner_id):
        await access_denied(message)
        return

    await state.update_data(owner_id=owner_id)
    await state.set_state(LeadForm.name)
    await message.answer("Как вас зовут?")


@router.message(LeadForm.name)
async def get_name(message: Message, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("owner_id")

    if owner_id is None:
        await state.clear()
        await message.answer("Ошибка: не найден владелец заявки. Откройте персональную ссылку специалиста заново.")
        return

    if not await has_active_access(owner_id):
        await state.clear()
        await access_denied(message)
        return

    await state.update_data(name=message.text)
    await state.set_state(LeadForm.phone)
    await message.answer("Введите ваш номер телефона:")


@router.message(LeadForm.phone)
async def get_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("owner_id")

    if owner_id is None:
        await state.clear()
        await message.answer("Ошибка: не найден владелец заявки. Откройте персональную ссылку специалиста заново.")
        return

    if not await has_active_access(owner_id):
        await state.clear()
        await access_denied(message)
        return

    await state.update_data(phone=message.text)
    await state.set_state(LeadForm.comment)
    await message.answer("Кратко опишите, что вам нужно:")


@router.message(LeadForm.comment)
async def get_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("owner_id")

    if owner_id is None:
        await state.clear()
        await message.answer("Ошибка: не найден владелец заявки. Откройте персональную ссылку специалиста заново.")
        return

    if not await has_active_access(owner_id):
        await state.clear()
        await access_denied(message)
        return

    await state.update_data(comment=message.text)

    data = await state.get_data()
    await state.clear()

    await save_lead(
        owner_id=owner_id,
        name=data["name"],
        phone=data["phone"],
        comment=data["comment"],
        tg_user_id=message.from_user.id,
    )

    await message.answer(
        "✅ Заявка отправлена!\n\n"
        "Владелец бизнеса скоро с вами свяжется.",
        reply_markup=client_menu(),
    )

    text = (
        "🔔 Новая заявка!\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"💬 Комментарий: {data['comment']}\n\n"
        f"🆔 Telegram ID клиента: {message.from_user.id}"
    )

    await message.bot.send_message(owner_id, text)


@router.message(F.text == "📥 Мои заявки")
async def show_leads(message: Message):
    owner_id = message.from_user.id

    if not await has_active_access(owner_id):
        await access_denied(message)
        return

    leads = await get_all_leads(owner_id=owner_id, limit=10)

    if not leads:
        await message.answer("Заявок пока нет.")
        return

    text = "📥 Последние заявки:\n\n"

    for index, (name, phone, comment, created_at) in enumerate(leads, start=1):
        text += (
            f"{index}. 👤 {name}\n"
            f"📞 {phone}\n"
            f"💬 {comment}\n"
            f"🕒 {created_at}\n\n"
        )

    await message.answer(text[:4000])


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    owner_id = message.from_user.id

    if not await has_active_access(owner_id):
        await access_denied(message)
        return

    stats = await get_leads_stats(owner_id=owner_id)

    text = (
        "📊 Статистика заявок\n\n"
        f"📅 Сегодня: {stats['today']}\n"
        f"📆 За 7 дней: {stats['week']}\n"
        f"📦 Всего: {stats['total']}"
    )

    await message.answer(text)


@router.message(F.text == "👥 Клиенты")
async def show_clients(message: Message):
    owner_id = message.from_user.id

    if not await has_active_access(owner_id):
        await access_denied(message)
        return

    clients = await get_unique_clients(owner_id=owner_id)

    if not clients:
        await message.answer("Клиентов пока нет.")
        return

    text = "👥 База клиентов\n\n"

    for index, (name, phone, leads_count) in enumerate(clients, start=1):
        text += (
            f"{index}. 👤 {name}\n"
            f"📞 {phone}\n"
            f"📝 Заявок: {leads_count}\n\n"
        )

    await message.answer(text[:4000])


@router.message(F.text == "💳 Подписка")
async def show_subscription(message: Message):
    owner_id = message.from_user.id
    subscription = await get_subscription(owner_id)

    status, started_at, paid_until = subscription

    paid_until_dt = datetime.fromisoformat(paid_until)
    now = datetime.now()

    days_left = (paid_until_dt - now).days
    if days_left < 0:
        days_left = 0

    if now > paid_until_dt:
        text = (
            "💳 Подписка\n\n"
            "⛔ Пробный период закончился.\n\n"
            "Чтобы продолжить пользоваться сервисом, оплатите подписку:\n"
            "💰 2 990 ₽ / месяц"
        )
    else:
        text = (
            "💳 Подписка\n\n"
            "🎁 Доступ активен\n"
            f"⏳ Осталось дней: {days_left}\n"
            f"📅 Доступ до: {paid_until_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            "После окончания пробного периода подписка — 2 990 ₽ / месяц."
        )

    await message.answer(text)

@router.message(F.text == "🔗 Моя ссылка")
async def show_personal_link(message: Message):
    owner_id = message.from_user.id

    config = load_config()
    bot_username = config.bot_username

    link = f"https://t.me/{bot_username}?start=owner_{owner_id}"

    text = (
        "🔗 Ваша персональная ссылка для приёма заявок:\n\n"
        f"{link}\n\n"
        "Отправьте эту ссылку своим клиентам.\n"
        "Когда они оставят заявку, вы сразу получите уведомление."
    )

    await message.answer(text)