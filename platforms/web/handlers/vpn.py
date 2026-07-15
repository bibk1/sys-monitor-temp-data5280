# platforms/web/handlers/vpn.py

import os
import json
import asyncio
from datetime import datetime

from modules.vpn.actions_VLESS import (
    get_vless_uris_in_range,
    get_total_vless_count,
    load_vless_run_metadata,
    load_vless_config,
    save_vless_config,
    SOURCES_FILE,
    CONFIG_FILE,
    RUSSIAN_CIDRS_FILE,
    load_russian_cidrs_fallback,
    save_russian_cidrs_fallback,
    run_vless_check
)

# Глобальная переменная для отслеживания состояния проверки
_CHECK_TASK = None

def get_vpn_summary():
    """Возвращает сводку о последней проверке."""
    meta = load_vless_run_metadata()
    if not meta:
        return {"last_run": None, "top_keys": []}

    # Форматируем дату
    ts = datetime.fromisoformat(meta["timestamp"])
    last_run = {
        "timestamp": ts.isoformat(),
        "formatted_time": ts.strftime("%d.%m.%Y %H:%M"),
        "duration_sec": meta["duration_sec"],
        "total_reality_keys": meta["total_reality_keys"],
        "available_servers": meta["available_servers"],
        "working_servers": meta["working_servers"]
    }

    # Топ-3 ключа
    top_keys = []
    uris = get_vless_uris_in_range(0, 3)
    for label, uri in uris:
        top_keys.append({"label": label, "uri": uri})

    return {"last_run": last_run, "top_keys": top_keys}


def get_vless_page(page: int, page_size: int = 10):
    """Возвращает одну страницу VLESS-ключей."""
    start = page * page_size
    end = start + page_size
    uris = get_vless_uris_in_range(start, end)
    total = get_total_vless_count()

    items = [{"label": label, "uri": uri} for label, uri in uris]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": end < total,
        "has_prev": page > 0
    }


def get_sources_content():
    """Возвращает содержимое vless_sources.txt."""
    if not os.path.exists(SOURCES_FILE):
        return ""
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def save_sources_content(content: str):
    """Сохраняет vless_sources.txt."""
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        f.write(content.strip())


def get_config_content():
    """Возвращает текущую конфигурацию как dict."""
    return load_vless_config()


def save_config_content(data: dict):
    """Сохраняет новую конфигурацию."""
    save_vless_config(data)


def get_russian_cidrs_content():
    """Возвращает список CIDR."""
    return load_russian_cidrs_fallback()


def save_russian_cidrs_content(cidrs: list[str]):
    """Сохраняет CIDR."""
    save_russian_cidrs_fallback(cidrs)


async def start_vless_check_background():
    """Запускает проверку в фоне."""
    global _CHECK_TASK
    if _CHECK_TASK and not _CHECK_TASK.done():
        raise RuntimeError("Проверка уже выполняется.")

    async def _run():
        await run_vless_check()

    _CHECK_TASK = asyncio.create_task(_run())
    return {"status": "started"}


def get_check_status():
    """Возвращает статус фоновой проверки."""
    global _CHECK_TASK
    if _CHECK_TASK is None:
        return {"running": False}
    if _CHECK_TASK.done():
        exc = _CHECK_TASK.exception()
        _CHECK_TASK = None
        if exc:
            return {"running": False, "error": str(exc)}
        return {"running": False, "success": True}
    return {"running": True}