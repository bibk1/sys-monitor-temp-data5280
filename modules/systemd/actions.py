# modules/systemd/action.py
import asyncio
import shutil
from typing import Tuple, Optional
from .config_loader import ServiceConfig, toggle_service_autostart

SUDO_CMD = ["sudo"] if shutil.which("sudo") else []

async def run_command(cmd: list[str]) -> Tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        out_text = stdout.decode('utf-8', errors='ignore').strip()
        err_text = stderr.decode('utf-8', errors='ignore').strip()
        
        if proc.returncode != 0:
            full_error = f"Код выхода: {proc.returncode}"
            if err_text: full_error += f"\nОшибка: {err_text}"
            if out_text: full_error += f"\nВывод: {out_text}"
            return False, full_error
        
        return True, out_text if out_text else "Выполнено успешно."
    except Exception as e:
        return False, f"Исключение: {str(e)}"

async def check_sudo_permissions() -> Tuple[bool, str]:
    cmd_test = SUDO_CMD + ["whoami"]
    success, output = await run_command(cmd_test)
    if not success: return False, "Нет доступа к sudo."
    return True, "Права доступны."

async def systemd_action(service: ServiceConfig, action: str) -> Tuple[bool, str]:
    svc_name = service.service_name
    base_cmd = SUDO_CMD + ["systemctl"]
    cmd = []
    
    if action == "start": 
        cmd = base_cmd + ["start", svc_name]
    elif action == "stop": 
        cmd = base_cmd + ["stop", svc_name]
    elif action == "restart": 
        cmd = base_cmd + ["restart", svc_name]
    elif action == "logs": 
        cmd = SUDO_CMD + ["journalctl", "-u", svc_name, "-n", "50", "--no-pager"]
    elif action == "enable_auto": 
        cmd = base_cmd + ["enable", svc_name]
    elif action == "disable_auto": 
        cmd = base_cmd + ["disable", svc_name]
    else: 
        return False, "Неизвестное действие"
    
    return await run_command(cmd)

async def get_service_status(service: ServiceConfig) -> str:
    cmd_active = SUDO_CMD + ["systemctl", "is-active", service.service_name]
    ok, out = await run_command(cmd_active)
    is_active = (ok and out.strip() == "active")
    
    auto_status = ""
    cmd_en = SUDO_CMD + ["systemctl", "is-enabled", service.service_name]
    ok_en, out_en = await run_command(cmd_en)
    if ok_en:
        st = out_en.strip()
        if st == "enabled": auto_status = " (Авто: ВКЛ)"
        elif st == "disabled": auto_status = " (Авто: ВЫКЛ)"
        else: auto_status = f" (Авто: {st})"
    
    if is_active: return f"🟢 Systemd: Активен{auto_status}"
    return f"🔴 Systemd: {out if out else 'Неактивен'}{auto_status}"

async def perform_action(service: ServiceConfig, action: str) -> Tuple[bool, str]:
    if action == "enable_auto": 
        return await systemd_action(service, "enable")
    if action == "disable_auto": 
        return await systemd_action(service, "disable")
    return await systemd_action(service, action)