from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Оставить заявку")],
            [KeyboardButton(text="ℹ️ О сервисе")],
        ],
        resize_keyboard=True,
    )


def owner_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Оставить заявку")],
            [KeyboardButton(text="📥 Мои заявки")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👥 Клиенты")],
            [KeyboardButton(text="💳 Подписка")],
            [KeyboardButton(text="🔗 Моя ссылка")],
            [KeyboardButton(text="ℹ️ О сервисе")],
        ],
        resize_keyboard=True,
    )