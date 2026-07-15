# platforms/telegram/keyboards/control.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_control_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔌 Выключить ПК", callback_data="control_shutdown")],
            [InlineKeyboardButton(text="🔄 Перезагрузить ПК", callback_data="control_reboot")],
            [InlineKeyboardButton(text="♻️ Перезапустить бота", callback_data="control_restart_bot")],
            [InlineKeyboardButton(text="🚫 Остановить бота", callback_data="control_stop_bot")]
            # ❌ Кнопка "Назад" удалена по вашему запросу
        ]
    )