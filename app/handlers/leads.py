from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.database import (
    get_owner_by_id,
    has_active_access_by_owner_id,
    save_lead,
)
from app.states.onboarding import LeadForm
from app.keyboards.main_menu import client_menu


router = Router()


CLIENT_LINK_TIME_LIMIT_MINUTES = 5


async def get_owner_id_from_state(state: FSMContext):
    data = await state.get_data()
    return data.get("owner_id")


async def is_client_link_still_valid(state: FSMContext) -> bool:
    data = await state.get_data()
    started_at = data.get("client_link_started_at")

    if not started_at:
        return False

    started_at_dt = datetime.fromisoformat(started_at)
    expires_at = started_at_dt + timedelta(minutes=CLIENT_LINK_TIME_LIMIT_MINUTES)

    return datetime.now(started_at_dt.tzinfo) <= expires_at


async def deny_client_access(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⛔ Время заполнения заявки истекло.\n\n"
        "Пожалуйста, откройте ссылку специалиста заново."
    )


@router.message(F.text == "📝 Оставить заявку")
async def restart_lead_form(message: Message, state: FSMContext):
    owner_id = await get_owner_id_from_state(state)

    if owner_id is None:
        await message.answer(
            "Чтобы оставить заявку, откройте персональную ссылку специалиста."
        )
        return

    if not await is_client_link_still_valid(state):
        await deny_client_access(message, state)
        return

    if not await has_active_access_by_owner_id(owner_id):
        await state.clear()
        await message.answer(
            "⛔ Сейчас специалист не принимает заявки через LeadNotifyBot.\n\n"
            "Попросите владельца связаться с вами напрямую."
        )
        return

    await state.set_state(LeadForm.name)
    await message.answer("Как Вас зовут?", reply_markup=client_menu())


@router.message(LeadForm.name)
async def get_name(message: Message, state: FSMContext):
    owner_id = await get_owner_id_from_state(state)

    if owner_id is None:
        await state.clear()
        await message.answer(
            "Ошибка: не найден владелец заявки.\n"
            "Откройте персональную ссылку специалиста заново."
        )
        return

    if not await is_client_link_still_valid(state):
        await deny_client_access(message, state)
        return

    if not await has_active_access_by_owner_id(owner_id):
        await state.clear()
        await message.answer(
            "⛔ Сейчас специалист не принимает заявки через LeadNotifyBot.\n\n"
            "Попросите владельца связаться с вами напрямую."
        )
        return

    await state.update_data(name=message.text)
    await state.set_state(LeadForm.contact)

    await message.answer(
        "Как с Вами связаться?\n\n"
        "Укажите номер телефона, Telegram username или VK."
    )


@router.message(LeadForm.contact)
async def get_contact(message: Message, state: FSMContext):
    owner_id = await get_owner_id_from_state(state)

    if owner_id is None:
        await state.clear()
        await message.answer(
            "Ошибка: не найден владелец заявки.\n"
            "Откройте персональную ссылку специалиста заново."
        )
        return

    if not await is_client_link_still_valid(state):
        await deny_client_access(message, state)
        return

    if not await has_active_access_by_owner_id(owner_id):
        await state.clear()
        await message.answer(
            "⛔ Сейчас специалист не принимает заявки через LeadNotifyBot.\n\n"
            "Попросите владельца связаться с вами напрямую."
        )
        return

    await state.update_data(contact=message.text)
    await state.set_state(LeadForm.comment)

    await message.answer("Комментарий: что хотите?")


@router.message(LeadForm.comment)
async def get_comment(message: Message, state: FSMContext):
    owner_id = await get_owner_id_from_state(state)

    if owner_id is None:
        await state.clear()
        await message.answer(
            "Ошибка: не найден владелец заявки.\n"
            "Откройте персональную ссылку специалиста заново."
        )
        return

    if not await is_client_link_still_valid(state):
        await deny_client_access(message, state)
        return

    if not await has_active_access_by_owner_id(owner_id):
        await state.clear()
        await message.answer(
            "⛔ Сейчас специалист не принимает заявки через LeadNotifyBot.\n\n"
            "Попросите владельца связаться с вами напрямую."
        )
        return

    await state.update_data(comment=message.text)
    data = await state.get_data()

    owner = await get_owner_by_id(owner_id)

    if not owner:
        await state.clear()
        await message.answer(
            "Ошибка: владелец заявки не найден.\n"
            "Откройте персональную ссылку специалиста заново."
        )
        return

    owner_tg_user_id = owner[1]

    await save_lead(
        owner_id=owner_id,
        client_tg_user_id=message.from_user.id,
        client_username=message.from_user.username,
        name=data["name"],
        contact=data["contact"],
        comment=data["comment"],
    )

    await state.clear()

    await message.answer(
        "✅ Заявка отправлена!\n\n"
        "Владелец бизнеса скоро с вами свяжется.",
        reply_markup=client_menu(),
    )

    client_username = message.from_user.username

    if client_username:
        tg_username_text = f"@{client_username}"
    else:
        tg_username_text = "не указан"

    notification_text = (
        "🔔 Новая заявка!\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Контакт: {data['contact']}\n"
        f"💬 Комментарий: {data['comment']}\n\n"
        f"🆔 Telegram ID клиента: {message.from_user.id}\n"
        f"📨 Telegram username: {tg_username_text}"
    )

    await message.bot.send_message(owner_tg_user_id, notification_text)