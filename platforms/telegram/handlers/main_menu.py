# platforms/telegram/handlers/main_menu.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.config import is_user_allowed

from platforms.telegram.keyboards.main_menu import get_main_menu_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обрабатывает команду /start."""
    if not is_user_allowed(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "👋 Добро пожаловать!\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(lambda message: message.text == "📊 Мониторинг")
async def handle_monitoring_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    from platforms.telegram.handlers.monitoring import show_monitoring
    await show_monitoring(message)

@router.message(lambda message: message.text == "🕹️ Управление")
async def handle_control_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    from platforms.telegram.handlers.control import show_control_menu
    await show_control_menu(message)

@router.message(lambda message: message.text == "🌐 Сеть")
async def handle_network_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    from platforms.telegram.handlers.network import show_network
    await show_network(message)

@router.message(lambda message: message.text == "🔑 VPN ключи")
async def handle_vpn_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    from platforms.telegram.handlers.vpn import show_vpn_menu
    await show_vpn_menu(message)

@router.message(lambda message: message.text == "🐳 Docker")
async def handle_docker_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    
    from platforms.telegram.handlers.docker import get_fresh_services_data, send_or_edit_list
    
    items = await get_fresh_services_data()
    if not items:
        await message.answer("❌ Список Docker сервисов пуст. Проверьте `modules/docker/services.yaml`.")
        return

    await send_or_edit_list(message, items, 0)

@router.message(lambda message: message.text == "⚙️ Systemd")
async def handle_systemd_button(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    
    from platforms.telegram.handlers.systemd import get_fresh_services_data, send_or_edit_list
    
    items = await get_fresh_services_data()
    if not items:
        await message.answer("❌ Список Systemd служб пуст. Проверьте `modules/systemd/services.yaml`.")
        return

    await send_or_edit_list(message, items, 0)