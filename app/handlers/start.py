from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

from app.database import (
    get_or_create_owner,
    get_owner_by_id,
    get_owner_by_tg_user_id,
    has_active_access_by_owner_id,
)
from app.keyboards.main_menu import (
    start_owner_menu,
    active_owner_menu,
    expired_owner_menu,
    client_menu,
)
from app.states.onboarding import LeadForm


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Клиент перешёл по персональной ссылке владельца:
    # /start owner_1
    if command.args and command.args.startswith("owner_"):
        try:
            owner_id = int(command.args.replace("owner_", ""))
        except ValueError:
            await message.answer("Некорректная ссылка для заявки.")
            return

        owner = await get_owner_by_id(owner_id)

        if not owner:
            await message.answer(
                "Ссылка недействительна.\n\n"
                "Попросите владельца отправить вам актуальную ссылку."
            )
            return

        has_access = await has_active_access_by_owner_id(owner_id)

        if not has_access:
            owner_tg_user_id = owner[1]

            await message.answer(
                "⛔ Сейчас специалист не принимает заявки через LeadNotifyBot.\n\n"
                "Попросите владельца связаться с вами напрямую."
            )

            try:
                await message.bot.send_message(
                    owner_tg_user_id,
                    "⚠️ Клиент попытался оставить заявку по вашей ссылке, "
                    "но пробный период или подписка закончились.\n\n"
                    "Чтобы снова принимать заявки, приобретите подписку "
                    "в разделе «Приобрести подписку!»."
                )
            except Exception:
                pass

            return

        await state.clear()
        await state.update_data(
            owner_id=owner_id,
            client_link_started_at=message.date.isoformat(),
        )

        await state.set_state(LeadForm.name)

        await message.answer(
            "Здравствуйте! 👋\n\n"
            "Заполните короткую заявку.\n\n"
            "Как Вас зовут?",
            reply_markup=client_menu(),
        )
        return

    # Обычный /start без ссылки.
    # Считаем, что это владелец бизнеса, который хочет подключить сервис.
    owner_id = await get_or_create_owner(
        tg_user_id=user_id,
        username=username,
        full_name=full_name,
    )

    has_access = await has_active_access_by_owner_id(owner_id)

    if has_access:
        await message.answer(
            "Привет! 👋\n\n"
            "Ваш доступ к LeadNotifyBot активен.\n"
            "Вы можете получать заявки, смотреть клиентов и статистику.",
            reply_markup=active_owner_menu(),
        )
        return

    subscription_owner = await get_owner_by_tg_user_id(user_id)

    if subscription_owner:
        await message.answer(
            "Привет! 👋\n\n"
            "Вы можете активировать пробный период на 3 дня "
            "или приобрести подписку.",
            reply_markup=start_owner_menu(),
        )
        return

    await message.answer(
        "Привет! 👋\n\n"
        "LeadNotifyBot помогает принимать заявки от клиентов прямо в Telegram.\n\n"
        "Вы можете активировать пробный период на 3 дня "
        "или приобрести подписку.",
        reply_markup=start_owner_menu(),
    )


@router.message(lambda message: message.text == "ℹ️ О сервисе")
async def about_handler(message: Message):
    await message.answer(
        "ℹ️ LeadNotifyBot — сервис для приёма заявок.\n\n"
        "Вы получаете персональную ссылку и отправляете её клиентам.\n"
        "Клиент заполняет короткую анкету, а заявка сразу приходит вам в Telegram.\n\n"
        "Это удобно для мастеров, тренеров, салонов, услуг и малого бизнеса."
    )