# modules/docker/action.py
import asyncio
import subprocess
import shutil
import os
from typing import Tuple, Optional, List
from .config_loader import ServiceConfig, toggle_service_autostart

# Определяем команду sudo
SUDO_CMD = ["sudo"] if shutil.which("sudo") else []

async def run_command(cmd: list[str]) -> Tuple[bool, str]:
    """Запускает команду без смены директории."""
    return await run_command_with_cwd(cmd, cwd=None)

async def run_command_with_cwd(cmd: list[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """Запускает команду с указанной рабочей директорией."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
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

# --- Docker Actions ---

async def docker_compose_action(service: ServiceConfig, action: str, autostart_enabled: bool = False) -> Tuple[bool, str]:
    if not service.path:
        return False, "Путь не указан."
    
    compose_file = os.path.join(service.path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(service.path, "compose.yaml")
        if not os.path.exists(compose_file):
            return False, "Файл docker-compose.yml не найден."

    work_dir = service.path
    base_cmd = SUDO_CMD + ["docker", "compose", "-f", compose_file]

    if action == "start":
        cmd = base_cmd + ["up", "-d"]
        # Если включен автозапуск, применим политику после старта
        if autostart_enabled:
            await _apply_restart_policy(base_cmd, work_dir, "always")
        return await run_command_with_cwd(cmd, work_dir)
        
    elif action == "stop":
        cmd = base_cmd + ["stop"]
        success, msg = await run_command_with_cwd(cmd, work_dir)
        if success: msg = "Контейнер остановлен, но не удален."
        return success, msg
        
    elif action == "restart":
        # Шаг 1: Полная остановка и удаление контейнеров
        down_cmd = base_cmd + ["down"]
        success_down, msg_down = await run_command_with_cwd(down_cmd, work_dir)
        if not success_down:
            return False, f"Ошибка при остановке: {msg_down}"
        
        # Шаг 2: Запуск заново
        up_cmd = base_cmd + ["up", "-d", "--force-recreate"]
        success_up, msg_up = await run_command_with_cwd(up_cmd, work_dir)
        
        if not success_up:
            return False, f"Ошибка при запуске: {msg_up}"
            
        # Шаг 3: Применяем политику перезапуска отдельно (надежнее чем флаг в up)
        policy = "always" if autostart_enabled else "no"
        await _apply_restart_policy(base_cmd, work_dir, policy)
        
        return True, "Контейнер перезапущен."
        
    elif action == "logs":
        cmd = base_cmd + ["logs", "--tail", "50"]
        return await run_command_with_cwd(cmd, work_dir)
        
    elif action in ["enable_auto", "disable_auto"]:
        return await set_docker_autostart(service, action == "enable_auto")
    
    return False, "Неизвестное действие"

async def _apply_restart_policy(base_cmd: list, work_dir: str, policy: str):
    """Вспомогательная функция для применения политики restart через docker update."""
    try:
        ps_cmd = base_cmd + ["ps", "-q"]
        success, output = await run_command_with_cwd(ps_cmd, work_dir)
        if success and output:
            container_ids = [cid.strip() for cid in output.split('\n') if cid.strip()]
            if container_ids:
                update_cmd = SUDO_CMD + ["docker", "update", f"--restart={policy}"] + container_ids
                await run_command(update_cmd)
    except Exception:
        pass # Игнорируем ошибки применения политики, если основной запуск прошел успешно

async def set_docker_autostart(service: ServiceConfig, enable: bool) -> Tuple[bool, str]:
    if not service.path: return False, "Путь не указан."
    compose_file = os.path.join(service.path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(service.path, "compose.yaml")
        if not os.path.exists(compose_file): return False, "Файл не найден."

    work_dir = service.path
    policy = "always" if enable else "no"
    
    # Сначала убедимся, что контейнеры запущены
    ps_cmd = SUDO_CMD + ["docker", "compose", "-f", compose_file, "ps", "-q"]
    success, output = await run_command_with_cwd(ps_cmd, work_dir)
    
    container_ids = [cid.strip() for cid in output.split('\n') if cid.strip()] if success and output else []
    
    if container_ids:
        update_cmd = SUDO_CMD + ["docker", "update", f"--restart={policy}"] + container_ids
        success, msg = await run_command(update_cmd)
        if not success: return False, f"Ошибка политики: {msg}"
        status_text = "ВКЛЮЧЕН (always)" if enable else "ВЫКЛЮЧЕН (no)"
        return True, f"Автозапуск {status_text}. Вступит в силу после перезагрузки ПК."
    else:
        # Если контейнеры не запущены, запускаем их с нужной политикой
        base_cmd = SUDO_CMD + ["docker", "compose", "-f", compose_file]
        cmd = base_cmd + ["up", "-d", "--force-recreate"]
        res = await run_command_with_cwd(cmd, work_dir)
        if res[0]:
            # После запуска применяем политику
            await _apply_restart_policy(base_cmd, work_dir, policy)
            return True, f"Автозапуск настроен ({policy}). Контейнер создан."
        return res

# --- File Editing Helpers ---

async def read_compose_file(service: ServiceConfig) -> Tuple[bool, str]:
    if not service.path: return False, "Путь не указан."
    compose_file = os.path.join(service.path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(service.path, "compose.yaml")
        if not os.path.exists(compose_file): return False, "Файл не найден."
    try:
        with open(compose_file, 'r', encoding='utf-8') as f: return True, f.read()
    except PermissionError:
        return await run_command(SUDO_CMD + ["cat", compose_file])
    except Exception as e: return False, str(e)

async def write_compose_file(service: ServiceConfig, content: str) -> Tuple[bool, str]:
    if not service.path: return False, "Путь не указан."
    compose_file = os.path.join(service.path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(service.path, "compose.yaml")
        if not os.path.exists(compose_file): compose_file = os.path.join(service.path, "docker-compose.yml")
    try:
        with open(compose_file, 'w', encoding='utf-8') as f: f.write(content)
        return True, "Файл сохранен."
    except PermissionError:
        try:
            proc = await asyncio.create_subprocess_exec("sudo", "tee", compose_file, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate(input=content.encode('utf-8'))
            if proc.returncode == 0: return True, "Файл сохранен (sudo)."
            return False, stderr.decode('utf-8', errors='ignore')
        except Exception as e: return False, f"Ошибка sudo: {str(e)}"
    except Exception as e: return False, str(e)

# --- Status & Unified Interface ---

async def get_service_status(service: ServiceConfig) -> str:
    if not service.path: return "❌ Путь не указан"
    compose_file = os.path.join(service.path, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(service.path, "compose.yaml")
        if not os.path.exists(compose_file): return "❌ Файл не найден"
    
    cmd = SUDO_CMD + ["docker", "compose", "-f", compose_file, "ps", "--format", "table {{.Name}}\t{{.Status}}"]
    success, out = await run_command_with_cwd(cmd, service.path)
    if not success: return f"⚪ Ошибка: {out}"
    
    lines = out.strip().split('\n')
    containers_info = [l for l in lines if l.strip() and "NAME" not in l.upper()]
    
    if not containers_info: return "🔴 Docker: Остановлен"
    running = sum(1 for l in containers_info if "Up" in l)
    
    if running == 0: return "🔴 Docker: Остановлен"
    if running == len(containers_info): return f"🟢 Docker: Работает ({running}/{len(containers_info)})"
    return f"🟡 Docker: Частично ({running}/{len(containers_info)})"

async def perform_action(service: ServiceConfig, action: str) -> Tuple[bool, str]:
    if action in ["enable_auto", "disable_auto"]:
        return await set_docker_autostart(service, action == "enable_auto")
    return await docker_compose_action(service, action, service.autostart)