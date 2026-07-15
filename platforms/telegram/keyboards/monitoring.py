# platforms/telegram/keyboards/monitoring.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_monitoring_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="monitoring_refresh")]
        ]
    )