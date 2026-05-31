from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def start_owner_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎁 Пробный период 3 дня"),
            ],
            [
                KeyboardButton(text="💳 Приобрести подписку"),
            ],
            [
                KeyboardButton(text="ℹ️ О сервисе"),
            ],
        ],
        resize_keyboard=True,
    )


def active_owner_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔗 Моя ссылка"),
            ],
            [
                KeyboardButton(text="📥 Мои заявки"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [
                KeyboardButton(text="👥 Клиенты"),
                KeyboardButton(text="💳 Подписка"),
            ],
            [
                KeyboardButton(text="ℹ️ О сервисе"),
            ],
        ],
        resize_keyboard=True,
    )


def expired_owner_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💳 Приобрести подписку"),
            ],
            [
                KeyboardButton(text="ℹ️ О сервисе"),
            ],
        ],
        resize_keyboard=True,
    )


def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Оставить заявку"),
            ],
            [
                KeyboardButton(text="ℹ️ О сервисе"),
            ],
        ],
        resize_keyboard=True,
    )


def tariffs_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💳 399 ₽ / месяц"),
            ],
            [
                KeyboardButton(text="🔥 2999 ₽ / год"),
            ],
            [
                KeyboardButton(text="⬅️ Назад"),
            ],
        ],
        resize_keyboard=True,
    )