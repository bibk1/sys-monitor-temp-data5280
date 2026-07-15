# platforms/web/handlers/network.py

from modules.network.actions import get_network_info

def get_network_data():
    """
    Аналог show_network() из Telegram.
    Возвращает структурированные сетевые данные для веба.
    """
    data = get_network_info()
    return data