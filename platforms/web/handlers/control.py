# platforms/web/handlers/control.py

import os
from modules.control.actions import shutdown_system, reboot_system, restart_bot_process

def trigger_shutdown():
    """Выключает систему."""
    shutdown_system()
    return {"status": "ok", "message": "Выключение инициировано."}

def trigger_reboot():
    """Перезагружает систему."""
    reboot_system()
    return {"status": "ok", "message": "Перезагрузка инициирована."}

def trigger_stop_bot():
    """Останавливает бота и завершает процесс."""
    # Поскольку у нас нет application в вебе, просто завершаем процесс
    os._exit(0)

def trigger_restart_bot():
    """Перезапускает бота."""
    restart_bot_process()
    # Эта строка не выполнится — execv заменяет процесс
    return {"status": "ok", "message": "Бот перезапускается..."}