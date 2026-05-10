import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

from app.config import load_config
from app.database import init_db, init_subscription
from app.handlers.leads import router as leads_router
from app.handlers.admin import router as admin_router
from app.keyboards.main_menu import client_menu, owner_menu


def is_owner(user_id: int) -> bool:
    config = load_config()
    return user_id in config.admin_ids


async def start_handler(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id

    if command.args and command.args.startswith("owner_"):
        try:
            owner_id = int(command.args.replace("owner_", ""))
        except ValueError:
            await message.answer("Некорректная ссылка для заявки.")
            return

        await state.update_data(owner_id=owner_id)

        await message.answer(
            "Привет! 👋\n\n"
            "Вы можете оставить заявку, а владелец бизнеса сразу получит уведомление.",
            reply_markup=client_menu(),
        )
        return

    if is_owner(user_id):
        await message.answer(
            "Привет, владелец бизнеса! 👋\n\n"
            "Здесь вы можете принимать заявки, смотреть статистику и управлять клиентами.",
            reply_markup=owner_menu(),
        )
    else:
        await message.answer(
            "Привет! 👋\n\n"
            "Чтобы оставить заявку, перейдите по ссылке, которую вам отправил специалист.",
            reply_markup=client_menu(),
        )


async def about_handler(message: Message):
    await message.answer(
        "ℹ️ LeadNotifyBot — сервис для приёма заявок.\n\n"
        "Клиенты оставляют заявку, а владелец бизнеса получает уведомление и видит данные в Telegram CRM."
    )


async def main():
    await init_db()
    await init_subscription()

    config = load_config()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    dp.include_router(leads_router)
    dp.include_router(admin_router)

    dp.message.register(start_handler, CommandStart())
    dp.message.register(about_handler, lambda message: message.text == "ℹ️ О сервисе")

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())