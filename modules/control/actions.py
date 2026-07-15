# modules/control/actions.py
import subprocess
import os
import sys

def shutdown_system():
    """Инициирует выключение системы через systemctl."""
    subprocess.Popen(["sudo", "systemctl", "poweroff", "-i"])

def reboot_system():
    """Инициирует перезагрузку системы через systemctl."""
    subprocess.Popen(["sudo", "systemctl", "reboot", "-i"])

def stop_bot_gracefully(application):
    """
    Останавливает бота и завершает процесс.
    Используется только внутри Telegram/VK адаптера.
    """
    import asyncio
    async def _shutdown():
        await application.stop()
        await application.shutdown()
        os._exit(0)
    asyncio.create_task(_shutdown())

def restart_bot(application):
    """
    Грациозно останавливает бота и перезапускает его с теми же аргументами.
    """
    import asyncio
    async def _restart():
        await application.stop()
        await application.shutdown()
        # Перезапуск с теми же параметрами
        python = sys.executable
        os.execv(python, [python] + sys.argv)
    asyncio.create_task(_restart())

def restart_bot_process():
    """
    Перезапускает текущий процесс Python с теми же аргументами.
    Используется в веб-интерфейсе.
    """
    python = sys.executable
    os.execv(python, [python] + sys.argv)