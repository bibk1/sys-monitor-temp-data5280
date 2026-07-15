from modules.systemd.config_loader import load_services, get_service_by_id, toggle_service_autostart, CONFIG_FILE as SYSTEMD_CONFIG_FILE
from modules.systemd.actions import (
    get_service_status, 
    perform_action, 
    check_sudo_permissions
)

PAGE_SIZE = 5

async def get_systemd_services_data(page: int):
    services = load_services()
    total = len(services)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = services[start:end]
    
    items = []
    for svc in page_items:
        status_text = await get_service_status(svc)
        items.append({
            "id": svc.id,
            "name": svc.name,
            "status": status_text,
            "autostart": svc.autostart
        })
        
    return {
        "total": total,
        "page": page,
        "has_next": end < total,
        "has_prev": page > 0,
        "items": items
    }

async def get_systemd_service_details_data(service_id: str):
    service = get_service_by_id(service_id)
    if not service:
        return None
    
    status_text = await get_service_status(service)
    return {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "status": status_text,
        "autostart": service.autostart,
        "service_name": service.service_name
    }

async def execute_systemd_action(service_id: str, action: str):
    service = get_service_by_id(service_id)
    if not service:
        return {"status": "error", "message": "Сервис не найден"}
    
    success, msg = await perform_action(service, action)
    return {"status": "ok" if success else "error", "message": msg}

async def get_systemd_logs_data(service_id: str):
    service = get_service_by_id(service_id)
    if not service:
        return {"status": "error", "message": "Сервис не найден"}
    
    # В actions.py нет отдельной функции для логов, используем perform_action с action='logs'
    success, msg = await perform_action(service, "logs")
    return {"status": "ok" if success else "error", "content": msg}

def get_systemd_services_yaml_content():
    try:
        with open(SYSTEMD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return {"status": "ok", "content": f.read()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def save_systemd_services_yaml_content(content: str):
    try:
        with open(SYSTEMD_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "ok", "message": "Конфигурация сохранена"}
    except Exception as e:
        return {"status": "error", "message": str(e)}