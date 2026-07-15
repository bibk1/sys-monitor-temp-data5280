# main.py
import asyncio
import sys
import threading
import time
import signal
from core.config import (
    ENABLE_TELEGRAM, 
    ENABLE_VK, 
    ENABLE_WEB,
    WEB_HOST,
    WEB_PORT,
    TG_MODE,
    LOCAL_API_CONFIG,
    LOCAL_API_ENV,
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH
)
from core.local_api_manager import LocalApiManager

# Глобальная переменная для менеджера API
local_api_manager = None

def run_web_server():
    """Запуск FastAPI в отдельном потоке."""
    import uvicorn
    config = uvicorn.Config(
        "platforms.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning",
        reload=False,
    )
    server = uvicorn.Server(config)
    server.run()

async def shutdown_process(signum=None, frame=None):
    """Обработчик корректного завершения работы."""
    print("\n🛑 Получен сигнал остановки. Завершение работы...")
    
    global local_api_manager
    if local_api_manager and TG_MODE == "local":
        print("⏹️ Остановка Local Bot API контейнера...")
        success, msg = await local_api_manager.stop()
        if success:
            print(f"✅ Контейнер остановлен: {msg}")
        else:
            print(f"⚠️ Не удалось остановить контейнер: {msg}")
    
    # Завершаем все задачи
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print("👋 Работа завершена.")
    sys.exit(0)

async def main():
    global local_api_manager
    tasks = []
    active_platforms = []
    telegram_url = None

    # 1. Запуск Веб-интерфейса
    if ENABLE_WEB:
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        time.sleep(0.5)
        print(f"🌐 Веб-интерфейс запущен на http://{WEB_HOST}:{WEB_PORT}")
        active_platforms.append("Web")
    else:
        print("⚠️ Веб-интерфейс отключен.")

    # 2. Подготовка Telegram
    if ENABLE_TELEGRAM:
        if TG_MODE == "local":
            print("🐳 Режим Telegram: LOCAL (Docker)")
            
            # Проверка обязательных переменных
            if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
                print("❌ ОШИБКА: Для режима 'local' необходимы TELEGRAM_API_ID и TELEGRAM_API_HASH в .env")
                print("⚠️ Переключение в режим CLOUD (fallback)...")
                TG_MODE_FINAL = "cloud"
            else:
                TG_MODE_FINAL = "local"
                # Инициализация менеджера
                local_api_manager = LocalApiManager(LOCAL_API_CONFIG, LOCAL_API_ENV)
                
                # Попытка запуска контейнера
                print("🔄 Проверка статуса контейнера...")
                if not await local_api_manager.is_running():
                    print("🚀 Запуск контейнера Local Bot API...")
                    success, msg = await local_api_manager.start()
                    if not success:
                        print(f"❌ Не удалось запустить контейнер: {msg}")
                        print("⚠️ Переключение в режим CLOUD (fallback)...")
                        TG_MODE_FINAL = "cloud"
                    else:
                        # Ждем готовности порта
                        ready = await local_api_manager.wait_ready(timeout=30)
                        if not ready:
                            print("⚠️ Контейнер запущен, но порт не отвечает. Переключение на CLOUD...")
                            TG_MODE_FINAL = "cloud"
                        else:
                            telegram_url = f"http://{LOCAL_API_CONFIG.get('host')}:{LOCAL_API_CONFIG.get('port')}"
                else:
                    print("✅ Контейнер уже запущен.")
                    # Все равно проверим порт
                    ready = await local_api_manager.wait_ready(timeout=10)
                    if ready:
                        telegram_url = f"http://{LOCAL_API_CONFIG.get('host')}:{LOCAL_API_CONFIG.get('port')}"
                    else:
                        print("⚠️ Порт не отвечает. Переключение на CLOUD...")
                        TG_MODE_FINAL = "cloud"
        else:
            print("☁️ Режим Telegram: CLOUD")
            TG_MODE_FINAL = "cloud"

        # Запуск бота (в любом случае, даже если fallback)
        from platforms.telegram.bot import start_telegram_bot
        # Передаем URL только если режим локальный и все прошло успешно
        url_to_use = telegram_url if (TG_MODE_FINAL == "local" and telegram_url) else None
        
        tasks.append(asyncio.create_task(start_telegram_bot(local_api_url=url_to_use)))
        active_platforms.append("Telegram")
    else:
        print("⚠️ Telegram отключен в конфиге.")

    if ENABLE_VK:
        print("⚠️ VK поддержка отключена (заглушка)")

    if not active_platforms:
        print("❌ Критическая ошибка: Ни одна платформа не активна.")
        sys.exit(1)

    print(f"✅ Система активна. Модули: {', '.join(active_platforms)}")

    # Регистрация обработчиков сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown_process(s)))

    if tasks:
        await asyncio.gather(*tasks)
    else:
        # Если только веб, держим процесс
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await shutdown_process()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Обработано внутри
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)