# platforms/telegram/handlers/control.py
import os
import sys
from aiogram import types
from modules.control.actions import shutdown_system, reboot_system, restart_bot

async def show_control_menu(message: types.Message):
    text = "🖥️ <b>Управление ПК</b>\nВыберите действие:"
    from platforms.telegram.keyboards.control import get_control_keyboard
    await message.answer(text, parse_mode="HTML", reply_markup=get_control_keyboard())

async def handle_shutdown(callback: types.CallbackQuery):
    await callback.message.answer("Выполняется выключение ПК...")
    shutdown_system()
    await callback.answer()

async def handle_reboot(callback: types.CallbackQuery):
    await callback.message.answer("Выполняется перезагрузка ПК...")
    reboot_system()
    await callback.answer()

async def handle_stop_bot(callback: types.CallbackQuery):
    await callback.message.answer("Бот останавливается...")
    await callback.answer()
    # Просто завершаем процесс — нет смысла делать graceful shutdown для локального бота
    os._exit(0)

async def handle_restart_bot(callback: types.CallbackQuery):
    await callback.message.answer("♻️ Бот перезапускается...")
    await callback.answer()
    python = sys.executable
    os.execv(python, [python] + sys.argv)