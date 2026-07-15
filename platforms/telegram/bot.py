# platforms/telegram/bot.py
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import StateFilter
from core.config import TELEGRAM_BOT_TOKEN

# Главное меню
from platforms.telegram.handlers import main_menu

# Модуль: Мониторинг
from platforms.telegram.handlers.monitoring import refresh_monitoring

# Модуль: Управление
from platforms.telegram.handlers.control import handle_shutdown, handle_reboot, handle_stop_bot, handle_restart_bot

# Модуль: Сеть
from platforms.telegram.handlers.network import refresh_network

# Модуль: VPN
from platforms.telegram.handlers.vpn import (
    show_vless_initial,
    show_vless_page,
    start_vless_check,
    handle_edit_sources,
    handle_new_sources,
    handle_edit_config,
    handle_new_config,
    handle_edit_russian_cidrs,
    handle_new_russian_cidrs,
    handle_cancel_edit
)

# === ИМПОРТЫ ТЕРМИНАЛА УДАЛЕНЫ ===

# Состояния (VPN)
from platforms.telegram.states.vpn import VPNStates

# Модули Docker и Systemd
from platforms.telegram.handlers import docker as docker_handlers
from platforms.telegram.handlers import systemd as systemd_handlers


def create_telegram_bot(api_url: str = None):
    """
    Создает экземпляр бота.
    :param api_url: URL локального сервера Bot API (если используется).
    """
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")

    if api_url:
        print(f"🔗 Подключение к Local Bot API: {api_url}")
        bot = Bot(token=TELEGRAM_BOT_TOKEN, base_url=api_url)
    else:
        print("☁️ Подключение к Telegram Cloud API")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

    dp = Dispatcher(storage=MemoryStorage())

    # --- Регистрация роутеров ---

    # Главное меню
    dp.include_router(main_menu.router)

    # Мониторинг
    dp.callback_query.register(refresh_monitoring, F.data == "monitoring_refresh")

    # Управление
    dp.callback_query.register(handle_shutdown, F.data == "control_shutdown")
    dp.callback_query.register(handle_reboot, F.data == "control_reboot")
    dp.callback_query.register(handle_stop_bot, F.data == "control_stop_bot")
    dp.callback_query.register(handle_restart_bot, F.data == "control_restart_bot")

    # Сеть
    dp.callback_query.register(refresh_network, F.data == "network_refresh")

    # VPN
    dp.callback_query.register(show_vless_initial, F.data == "vpn_vless")
    dp.callback_query.register(show_vless_page, F.data.startswith("vpn_page:"))
    dp.callback_query.register(start_vless_check, F.data == "vpn_check_vless")
    dp.callback_query.register(handle_edit_sources, F.data == "vpn_edit_sources")
    dp.callback_query.register(handle_edit_config, F.data == "vpn_edit_config")
    dp.callback_query.register(handle_edit_russian_cidrs, F.data == "vpn_edit_russian_cidrs")
    dp.callback_query.register(handle_cancel_edit, F.data == "vpn_cancel_edit")

    # === ХЕНДЛЕРЫ ТЕРМИНАЛА УДАЛЕНЫ ===

    # FSM состояния для VPN
    dp.message.register(handle_new_sources, StateFilter(VPNStates.waiting_for_sources))
    dp.message.register(handle_new_config, StateFilter(VPNStates.waiting_for_config))
    dp.message.register(handle_new_russian_cidrs, StateFilter(VPNStates.waiting_for_russian_cidrs))

    # Модули Docker и Systemd
    dp.include_router(docker_handlers.router)
    dp.include_router(systemd_handlers.router)

    return bot, dp


async def start_telegram_bot(local_api_url: str = None):
    bot, dp = create_telegram_bot(api_url=local_api_url)
    try:
        print("✅ Запуск polling Telegram бота...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print("🔒 Сессия бота закрыта.")