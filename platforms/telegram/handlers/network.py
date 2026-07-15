# platforms/telegram/handlers/network.py
from aiogram import types
from modules.network.actions import get_network_info

async def show_network(message: types.Message):  # ← ИМЯ ИЗМЕНЕНО
    data = get_network_info()
    msg = _build_network_message(data)
    from platforms.telegram.keyboards.network import get_network_keyboard
    await message.answer(msg, parse_mode="HTML", reply_markup=get_network_keyboard())

async def refresh_network(callback: types.CallbackQuery):
    data = get_network_info()
    msg = _build_network_message(data)
    from platforms.telegram.keyboards.network import get_network_keyboard
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=get_network_keyboard())
    await callback.answer()

def _build_network_message(data: dict) -> str:
    return (
        "🌐 <b>Сетевая информация</b>\n\n"
        f"📶 Wi-Fi: <code>{data['ssid']}</code>\n"
        f"🏠 Локальный IP: <code>{data['local_ip']}</code>\n"
        f"🔌 MAC-адрес: <code>{data['mac_address']}</code>\n"
        f"🚪 Шлюз: <code>{data['gateway']}</code>\n"
        f"🌍 Внешний IP: <code>{data['external_ip']}</code>\n"
        f"🌐 Интернет: <b>{data['internet_status']}</b>\n"
        f"⏱️ Пинг (8.8.8.8): <b>{data['ping']}</b>"
    )