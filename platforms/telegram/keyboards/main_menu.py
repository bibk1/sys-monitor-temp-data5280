# platforms/telegram/keyboards/main_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Мониторинг"),
                KeyboardButton(text="🕹️ Управление")
            ],
            [
                KeyboardButton(text="🌐 Сеть"),
                KeyboardButton(text="🔑 VPN ключи")
            ],
            [
                KeyboardButton(text="🐳 Docker"),
                KeyboardButton(text="⚙️ Systemd")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )