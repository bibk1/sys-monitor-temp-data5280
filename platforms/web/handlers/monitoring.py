# platforms/web/handlers/monitoring.py

from modules.monitoring.actions import get_system_info

def get_monitoring_data():
    """
    Аналог show_monitoring() из Telegram.
    Возвращает структурированные данные для веба.
    """
    data = get_system_info()
    return data