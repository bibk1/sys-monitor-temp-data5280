#modules/docker/config_loader.py
import os
import yaml
from typing import List, Optional, Dict, Any

MODULE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(MODULE_DIR, "services.yaml")

class ServiceConfig:
    def __init__(self, data: dict):
        self.id = data.get("id", "unknown")
        self.name = data.get("name", self.id)
        self.path = data.get("path", "")
        self.description = data.get("description", "")
        self.autostart = data.get("autostart", False)
        # Тип всегда docker в этом модуле
        self.type = "docker"

def load_services() -> List[ServiceConfig]:
    if not os.path.exists(CONFIG_FILE):
        default_config = {"services": []}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
        except Exception as e:
            print(f"❌ Не удалось создать файл конфигурации Docker: {e}")
        return []

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        services = []
        if data and isinstance(data, dict) and "services" in data:
            for item in data["services"]:
                if isinstance(item, dict):
                    services.append(ServiceConfig(item))
        return services
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации Docker: {e}")
        return []

def get_service_by_id(service_id: str) -> Optional[ServiceConfig]:
    services = load_services()
    for svc in services:
        if svc.id == service_id:
            return svc
    return None

def _save_services_data(data: Dict[str, Any]) -> bool:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения конфигурации Docker: {e}")
        return False

def toggle_service_autostart(service_id: str, new_value: bool) -> bool:
    if not os.path.exists(CONFIG_FILE):
        return False
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or not isinstance(data, dict) or "services" not in data:
            return False

        found = False
        for item in data["services"]:
            if isinstance(item, dict) and item.get("id") == service_id:
                item["autostart"] = new_value
                found = True
                break
        
        if found:
            return _save_services_data(data)
        return False
    except Exception as e:
        print(f"❌ Ошибка при обновлении autostart Docker: {e}")
        return False