# core/config.py
import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"

def load_json_config():
    if not CONFIG_FILE.exists():
        print(f"⚠️ Файл конфигурации {CONFIG_FILE} не найден.")
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")
        return {}

CONFIG = load_json_config()

# --- Настройки платформ ---
PLATFORMS = CONFIG.get("platforms", {})
ENABLE_TELEGRAM = PLATFORMS.get("telegram", False)
ENABLE_VK = PLATFORMS.get("vk", False)
ENABLE_WEB = PLATFORMS.get("web", True)

# --- Настройки Web сервера ---
WEB_CONFIG = CONFIG.get("web_server", {})
WEB_HOST = WEB_CONFIG.get("host", "192.168.50.1")
WEB_PORT = WEB_CONFIG.get("port", 8001)

# --- Настройки Telegram (Local vs Cloud) ---
TG_CONFIG = CONFIG.get("telegram", {})
TG_MODE = TG_CONFIG.get("mode", "cloud")  # 'local' или 'cloud'
LOCAL_API_CONFIG = TG_CONFIG.get("local_api", {})

# Переменные для Local API
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Словарь окружения для передачи в менеджер Docker
LOCAL_API_ENV = {
    "TELEGRAM_API_ID": TELEGRAM_API_ID or "",
    "TELEGRAM_API_HASH": TELEGRAM_API_HASH or "",
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN or ""
}

# --- Безопасность ---
ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "")
if ALLOWED_USER_IDS_RAW.strip():
    ALLOWED_USER_IDS = [int(x.strip()) for x in ALLOWED_USER_IDS_RAW.split(",") if x.strip().isdigit()]
else:
    ALLOWED_USER_IDS = []

WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "password")

def is_user_allowed(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS