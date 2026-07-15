import os
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, Response, Cookie, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
import secrets

# Загрузка конфигурации (включая WEB_USERNAME/WEB_PASSWORD)
from core.config import WEB_USERNAME, WEB_PASSWORD

# Handlers
from platforms.web.handlers.monitoring import get_monitoring_data
from platforms.web.handlers.network import get_network_data
from platforms.web.handlers.control import trigger_shutdown, trigger_reboot, trigger_stop_bot, trigger_restart_bot
from platforms.web.handlers.vpn import (
    get_vpn_summary,
    get_vless_page,
    get_sources_content,
    save_sources_content,
    get_config_content,
    save_config_content,
    get_russian_cidrs_content,
    save_russian_cidrs_content,
    start_vless_check_background,
    get_check_status
)
# Добавлены импорты хендлеров Docker и Systemd
from platforms.web.handlers.docker import (
    get_docker_services_data,
    get_service_details_data,
    execute_docker_action,
    get_logs_data,
    get_compose_content,
    save_compose_content,
    get_services_yaml_content,
    save_services_yaml_content
)
from platforms.web.handlers.systemd import (
    get_systemd_services_data,
    get_systemd_service_details_data,
    execute_systemd_action,
    get_systemd_logs_data,
    get_systemd_services_yaml_content,
    save_systemd_services_yaml_content
)

app = FastAPI()

# === HTTP Basic Auth ===
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, WEB_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, WEB_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# === Шаблонизация без Jinja2 ===
def render_template(template_name: str, **context) -> str:
    base_path = Path(__file__).parent / "templates" / "base.html"
    content_path = Path(__file__).parent / "templates" / template_name

    base_html = base_path.read_text(encoding="utf-8")
    content_html = content_path.read_text(encoding="utf-8")

    title = context.get("title", "PC Control")
    result = base_html.replace("{% block title %}PC Control{% endblock %}", f"<title>{title}</title>")
    result = result.replace("{% block content %}{% endblock %}", content_html)
    return result


# === Все маршруты защищены аутентификацией ===

@app.get("/", response_class=HTMLResponse)
async def main_menu(_ = Depends(authenticate)):
    return HTMLResponse(render_template("main_menu.html", title="Главная"))


@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("monitoring.html", title="Мониторинг"))

@app.get("/api/monitoring/data")
async def api_monitoring_data(_ = Depends(authenticate)):
    return get_monitoring_data()


@app.get("/network", response_class=HTMLResponse)
async def network_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("network.html", title="Сеть"))

@app.get("/api/network/data")
async def api_network_data(_ = Depends(authenticate)):
    return get_network_data()


@app.get("/control", response_class=HTMLResponse)
async def control_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("control.html", title="Управление"))

@app.post("/api/control/shutdown")
async def api_control_shutdown(_ = Depends(authenticate)):
    return trigger_shutdown()

@app.post("/api/control/reboot")
async def api_control_reboot(_ = Depends(authenticate)):
    return trigger_reboot()

@app.post("/api/control/stop_bot")
async def api_control_stop_bot(_ = Depends(authenticate)):
    return trigger_stop_bot()

@app.post("/api/control/restart_bot")
async def api_control_restart_bot(_ = Depends(authenticate)):
    return trigger_restart_bot()

@app.get("/vpn", response_class=HTMLResponse)
async def vpn_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("vpn.html", title="VPN"))

@app.get("/api/vpn/summary")
async def api_vpn_summary(_ = Depends(authenticate)):
    return get_vpn_summary()

@app.get("/api/vpn/page/{page}")
async def api_vpn_page(page: int, _ = Depends(authenticate)):
    return get_vless_page(page)

@app.get("/api/vpn/sources")
async def api_vpn_sources(_ = Depends(authenticate)):
    return {"content": get_sources_content()}

@app.post("/api/vpn/sources")
async def api_vpn_save_sources(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    save_sources_content(body["content"])
    return {"status": "ok"}

@app.get("/api/vpn/config")
async def api_vpn_config(_ = Depends(authenticate)):
    return get_config_content()

@app.post("/api/vpn/config")
async def api_vpn_save_config(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    save_config_content(body)
    return {"status": "ok"}

@app.get("/api/vpn/cidrs")
async def api_vpn_cidrs(_ = Depends(authenticate)):
    return {"cidrs": get_russian_cidrs_content()}

@app.post("/api/vpn/cidrs")
async def api_vpn_save_cidrs(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    save_russian_cidrs_content(body["cidrs"])
    return {"status": "ok"}

@app.post("/api/vpn/check/start")
async def api_vpn_start_check(_ = Depends(authenticate)):
    await start_vless_check_background()
    return {"status": "ok"}

@app.get("/api/vpn/check/status")
async def api_vpn_check_status(_ = Depends(authenticate)):
    return get_check_status()

# === МАРШРУТЫ ДЛЯ DOCKER ===

@app.get("/docker", response_class=HTMLResponse)
async def docker_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("docker.html", title="Docker"))

@app.get("/api/docker/services")
async def api_docker_services(page: int = 0, _ = Depends(authenticate)):
    return await get_docker_services_data(page)

@app.get("/api/docker/service/{service_id}")
async def api_docker_service_details(service_id: str, _ = Depends(authenticate)):
    data = await get_service_details_data(service_id)
    if not data:
        raise HTTPException(status_code=404, detail="Service not found")
    return data

@app.post("/api/docker/action")
async def api_docker_action(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    return await execute_docker_action(body.get("service_id"), body.get("action"))

@app.get("/api/docker/logs/{service_id}")
async def api_docker_logs(service_id: str, _ = Depends(authenticate)):
    return await get_logs_data(service_id)

@app.get("/api/docker/compose/{service_id}")
async def api_get_compose(service_id: str, _ = Depends(authenticate)):
    return await get_compose_content(service_id)

@app.post("/api/docker/compose/{service_id}")
async def api_save_compose(service_id: str, request: Request, _ = Depends(authenticate)):
    body = await request.json()
    return await save_compose_content(service_id, body.get("content"))

@app.get("/api/docker/config/yaml")
async def api_get_services_yaml(_ = Depends(authenticate)):
    return get_services_yaml_content()

@app.post("/api/docker/config/yaml")
async def api_save_services_yaml(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    return save_services_yaml_content(body.get("content"))

# === НОВЫЕ МАРШРУТЫ ДЛЯ SYSTEMD ===

@app.get("/systemd", response_class=HTMLResponse)
async def systemd_page(_ = Depends(authenticate)):
    return HTMLResponse(render_template("systemd.html", title="Systemd"))

@app.get("/api/systemd/services")
async def api_systemd_services(page: int = 0, _ = Depends(authenticate)):
    return await get_systemd_services_data(page)

@app.get("/api/systemd/service/{service_id}")
async def api_systemd_service_details(service_id: str, _ = Depends(authenticate)):
    data = await get_systemd_service_details_data(service_id)
    if not data:
        raise HTTPException(status_code=404, detail="Service not found")
    return data

@app.post("/api/systemd/action")
async def api_systemd_action(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    return await execute_systemd_action(body.get("service_id"), body.get("action"))

@app.get("/api/systemd/logs/{service_id}")
async def api_systemd_logs(service_id: str, _ = Depends(authenticate)):
    return await get_systemd_logs_data(service_id)

@app.get("/api/systemd/config/yaml")
async def api_get_systemd_yaml(_ = Depends(authenticate)):
    return get_systemd_services_yaml_content()

@app.post("/api/systemd/config/yaml")
async def api_save_systemd_yaml(request: Request, _ = Depends(authenticate)):
    body = await request.json()
    return save_systemd_services_yaml_content(body.get("content"))