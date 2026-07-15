# platforms/telegram/keyboards/network.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_network_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="network_refresh")]
            # ❌ Кнопка "Назад" удалена по вашему стилю
        ]
    )