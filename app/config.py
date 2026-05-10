from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    bot_username: str


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN")
    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    bot_username = os.getenv("BOT_USERNAME")

    if not bot_token:
        raise ValueError("BOT_TOKEN не найден в .env")

    if not bot_username:
        raise ValueError("BOT_USERNAME не найден в .env")

    admin_ids = [
        int(admin_id.strip())
        for admin_id in admin_ids_raw.split(",")
        if admin_id.strip()
    ]

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        bot_username=bot_username,
    )