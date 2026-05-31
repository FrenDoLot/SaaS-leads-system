import asyncio

from aiogram import Bot, Dispatcher

from app.config import load_config
from app.database import init_db

from app.handlers.start import router as start_router
from app.handlers.billing import router as billing_router
from app.handlers.leads import router as leads_router
from app.handlers.owner import router as owner_router
from app.handlers.admin import router as admin_router


async def main():
    config = load_config()

    await init_db()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(billing_router)
    dp.include_router(leads_router)
    dp.include_router(owner_router)
    dp.include_router(admin_router)

    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())