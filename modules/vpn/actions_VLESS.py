#modules/vpn/actions_VLESS.py
import asyncio
import json
import os
import sys
import tempfile
import shutil
import time
from urllib.parse import urlparse, parse_qs
import urllib.request
import ipaddress
from datetime import datetime

# === Настройки по умолчанию ===
DEFAULT_CONFIG = {
    "FAST_CONCURRENT": 300,
    "FAST_TIMEOUT": 3,
    "PRECISE_CONCURRENT": 60,
    "PRECISE_TIMEOUT": 10,
    "SOCKS_PORT_START": 11000,
    "TEST_FILE_URL": "http://speedtest.tele2.net/1MB.zip"
}

# 🔑 Пути к файлам — строго внутри папки модуля
MODULE_DIR = os.path.dirname(__file__)
REPORT_FILE = os.path.join(MODULE_DIR, "vless_speed_report.csv")
METADATA_FILE = os.path.join(MODULE_DIR, "vless_last_run.json")
SOURCES_FILE = os.path.join(MODULE_DIR, "vless_sources.txt")
CONFIG_FILE = os.path.join(MODULE_DIR, "vless_config.json")
RUSSIAN_CIDRS_FILE = os.path.join(MODULE_DIR, "vless_russian_cidrs.json")

# Кэш для проверки IP
_russian_networks_cache = None
_ip_russia_cache = {}


def github_to_raw_url(url: str) -> str:
    url = url.strip()
    if "github.com" not in url:
        return url
    return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")


def load_russian_cidrs_fallback():
    """Загружает резервный список CIDR или создаёт по умолчанию."""
    default_cidrs = [
        "5.136.0.0/13", "31.128.0.0/11", "46.0.0.0/10", "77.37.0.0/16",
        "78.24.0.0/13", "80.64.0.0/13", "83.136.0.0/13", "85.172.0.0/14",
        "90.152.0.0/13", "91.122.0.0/15", "93.90.0.0/15", "94.180.0.0/14",
        "95.168.0.0/13", "109.184.0.0/13", "176.32.0.0/12", "178.176.0.0/12",
        "185.24.0.0/14", "188.124.0.0/14", "195.19.0.0/16", "195.210.0.0/16",
        "212.112.0.0/14", "213.87.0.0/16", "217.118.0.0/15"
    ]
    
    if not os.path.exists(RUSSIAN_CIDRS_FILE):
        save_russian_cidrs_fallback(default_cidrs)
        return default_cidrs
    
    try:
        with open(RUSSIAN_CIDRS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            return data
        else:
            raise ValueError("Неверный формат")
    except Exception:
        save_russian_cidrs_fallback(default_cidrs)
        return default_cidrs


def save_russian_cidrs_fallback(cidrs: list[str]):
    """Сохраняет резервный список CIDR."""
    with open(RUSSIAN_CIDRS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cidrs, f, ensure_ascii=False, indent=2)


async def fetch_russian_cidrs_from_ripe() -> list[str]:
    """Загружает список российских IPv4-диапазонов из RIPE Stat."""
    global _russian_networks_cache
    if _russian_networks_cache is not None:
        return _russian_networks_cache

    print("🌍 Загрузка списка российских IP из RIPE Stat...")
    try:
        url = "https://stat.ripe.net/data/country-resource-list/data.json?resource=RU"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (RealityChecker)'})

        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_data = resp.read()
            if not resp.getheader('Content-Type', '').startswith('application/json'):
                raise ValueError("Ответ не в формате JSON")
            data = json.loads(raw_data)

        resources = data.get('data', {}).get('resources', {})
        ipv4_list = resources.get('ipv4', [])

        if isinstance(ipv4_list, dict):
            ipv4_list = ipv4_list.get('prefixes', [])
        elif not isinstance(ipv4_list, list):
            ipv4_list = []

        cidrs = [str(item) for item in ipv4_list if isinstance(item, str) and '/' in item]
        _russian_networks_cache = sorted(set(cidrs))
        print(f"✅ Получено {len(_russian_networks_cache)} российских IPv4-диапазонов")
        return _russian_networks_cache

    except Exception as e:
        print(f"⚠️ Не удалось загрузить CIDR из RIPE: {e}. Используем резерв.")
        return load_russian_cidrs_fallback()


def is_russian_ip_cached(ip_str: str, russian_networks: list) -> bool:
    """Проверяет, принадлежит ли IP российскому диапазону (с кэшированием)."""
    global _ip_russia_cache
    if ip_str in _ip_russia_cache:
        return _ip_russia_cache[ip_str]

    try:
        ip = ipaddress.IPv4Address(ip_str)
        for cidr in russian_networks:
            if ip in ipaddress.IPv4Network(cidr):
                _ip_russia_cache[ip_str] = True
                return True
        _ip_russia_cache[ip_str] = False
        return False
    except Exception:
        _ip_russia_cache[ip_str] = False
        return False


def load_vless_sources() -> list[str]:
    """Загружает список URL из vless_sources.txt."""
    if not os.path.exists(SOURCES_FILE):
        default_content = (
            "# Список источников VLESS/REALITY-ключей (по одному URL на строку)\n"
            "https://github.com/kort0881/vpn-vless-configs-russia/blob/main/githubmirror/clean/vless.txt\n"
        )
        with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
            f.write(default_content)
        return ["https://github.com/kort0881/vpn-vless-configs-russia/blob/main/githubmirror/clean/vless.txt"]

    urls = []
    try:
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    urls.append(stripped)
    except Exception as e:
        raise RuntimeError(f"Не удалось прочитать {SOURCES_FILE}: {e}")

    if not urls:
        raise RuntimeError(f"Файл {SOURCES_FILE} не содержит ни одного URL.")

    return urls


def load_vless_config():
    """Загружает конфиг или создаёт по умолчанию."""
    if not os.path.exists(CONFIG_FILE):
        save_vless_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    except Exception:
        save_vless_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_vless_config(config: dict):
    """Сохраняет конфиг в файл."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


async def download_keys_from_github(url: str) -> list[str]:
    """Загружает и фильтрует REALITY-ключи из одного URL."""
    raw_url = github_to_raw_url(url)
    try:
        with urllib.request.urlopen(raw_url, timeout=10) as resp:
            content = resp.read().decode('utf-8')
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and stripped.startswith("vless://"):
                try:
                    parsed = urlparse(stripped)
                    query = parse_qs(parsed.query)
                    if query.get("security", [""])[0] == "reality":
                        lines.append(stripped)
                except:
                    continue
        return lines
    except Exception as e:
        print(f"⚠️ Пропущен источник {url}: {e}")
        return []


async def download_all_vless_keys() -> list[str]:
    """Загружает ключи из всех источников и объединяет их (без дубликатов)."""
    urls = load_vless_sources()
    all_keys = set()

    for url in urls:
        try:
            keys = await download_keys_from_github(url)
            all_keys.update(keys)
        except Exception as e:
            print(f"❌ Ошибка при обработке {url}: {e}")

    return list(all_keys)


async def fast_check_vless(uri: str) -> bool:
    try:
        parsed = urlparse(uri)
        host = parsed.hostname
        port = parsed.port or 443
        if not host:
            return False
    except:
        return False

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=FAST_TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False


async def precise_check_with_speed(uri: str, index: int, socks_port: int):
    config_path = None
    xray_proc = None

    try:
        parsed = urlparse(uri)
        uuid = parsed.username
        host = parsed.hostname
        port = parsed.port or 443
        query = parse_qs(parsed.query)

        if not uuid or not host:
            return None

        security = query.get("security", ["none"])[0]
        if security != "reality":
            return None

        pbk = query.get("pbk", [None])[0]
        if not pbk:
            return None

        sid = query.get("sid", [""])[0]
        spx = query.get("spx", [""])[0]
        fp = query.get("fp", ["chrome"])[0]
        sni = query.get("sni", [host])[0]
        type_ = query.get("type", ["tcp"])[0]

        config = {
            "log": {"loglevel": "error"},
            "inbounds": [{
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth"}
            }],
            "outbounds": [{
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": host,
                        "port": port,
                        "users": [{"id": uuid, "encryption": "none", "flow": ""}]
                    }]
                },
                "streamSettings": {
                    "network": type_,
                    "security": "reality",
                    "realitySettings": {
                        "publicKey": pbk,
                        "shortId": sid,
                        "spiderX": spx,
                        "fingerprint": fp,
                        "serverName": sni
                    }
                }
            }]
        }

        if type_ == "ws":
            path = query.get("path", ["/"])[0]
            host_header = query.get("host", [""])[0]
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "path": path,
                "headers": {"Host": host_header} if host_header else {}
            }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tf:
            json.dump(config, tf, ensure_ascii=False)
            config_path = tf.name

        xray_proc = await asyncio.create_subprocess_exec(
            "xray", "-config", config_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        await asyncio.sleep(0.15)

        proc = await asyncio.create_subprocess_exec(
            "curl",
            "-x", f"socks5h://127.0.0.1:{socks_port}",
            "--connect-timeout", "4",
            "--max-time", str(PRECISE_TIMEOUT),
            "-s", "-o", "/dev/null",
            "-w", "%{time_total},%{time_starttransfer},%{size_download}",
            TEST_FILE_URL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()

        if not output or ',' not in output:
            return None

        time_total, time_ttfb, size_bytes = output.split(',')
        time_total = float(time_total)
        time_ttfb = float(time_ttfb)
        size_bytes = int(float(size_bytes))

        if size_bytes < 50_000 or time_total < 0.1:
            return None

        speed_mbps = (size_bytes * 8) / time_total / 1_000_000
        ping_ms = time_ttfb * 1000
        return (speed_mbps, ping_ms)

    except:
        return None
    finally:
        if xray_proc and xray_proc.returncode is None:
            try:
                xray_proc.terminate()
                await asyncio.wait_for(xray_proc.wait(), timeout=1)
            except:
                xray_proc.kill()
        if config_path and os.path.exists(config_path):
            os.unlink(config_path)


# ================================
# ФУНКЦИИ ДЛЯ TELEGRAM-ИНТЕГРАЦИИ
# ================================

def get_vless_uris_in_range(start: int, end: int) -> list[tuple[str, str]]:
    if not os.path.exists(REPORT_FILE):
        return []

    try:
        with open(REPORT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return []

    data_lines = lines[1:]
    uris = []
    for line in data_lines[start:end]:
        parts = line.strip().split(',', 2)
        if len(parts) < 3:
            continue
        try:
            speed = float(parts[0])
            ping = int(float(parts[1]))
            uri = parts[2].strip()
            if uri.startswith("vless://"):
                label = f"{speed:.1f} Mbps / {ping} мс"
                uris.append((label, uri))
        except (ValueError, IndexError):
            continue
    return uris


def get_total_vless_count() -> int:
    if not os.path.exists(REPORT_FILE):
        return 0
    try:
        with open(REPORT_FILE, 'r', encoding='utf-8') as f:
            return max(0, len(f.readlines()) - 1)
    except Exception:
        return 0


def save_vless_run_metadata(
    total_reality_keys: int,
    available_servers: int,
    working_servers: int,
    duration_sec: float
):
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_reality_keys": total_reality_keys,
        "available_servers": available_servers,
        "working_servers": working_servers,
        "duration_sec": duration_sec
    }
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_vless_run_metadata() -> dict | None:
    if not os.path.exists(METADATA_FILE):
        return None
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# Глобальные переменные для совместимости
FAST_CONCURRENT = DEFAULT_CONFIG["FAST_CONCURRENT"]
FAST_TIMEOUT = DEFAULT_CONFIG["FAST_TIMEOUT"]
PRECISE_CONCURRENT = DEFAULT_CONFIG["PRECISE_CONCURRENT"]
PRECISE_TIMEOUT = DEFAULT_CONFIG["PRECISE_TIMEOUT"]
SOCKS_PORT_START = DEFAULT_CONFIG["SOCKS_PORT_START"]
TEST_FILE_URL = DEFAULT_CONFIG["TEST_FILE_URL"]


async def run_vless_check():
    """Запускает проверку всех источников и сохраняет результат (без российских IP)."""
    global FAST_CONCURRENT, FAST_TIMEOUT, PRECISE_CONCURRENT, PRECISE_TIMEOUT, SOCKS_PORT_START, TEST_FILE_URL

    start_time = time.time()

    if not shutil.which("xray"):
        raise RuntimeError("'xray' не найден. Установите: https://github.com/XTLS/Xray-core")
    if not shutil.which("curl"):
        raise RuntimeError("'curl' не найден.")

    # Загружаем настройки
    config = load_vless_config()
    FAST_CONCURRENT = config["FAST_CONCURRENT"]
    FAST_TIMEOUT = config["FAST_TIMEOUT"]
    PRECISE_CONCURRENT = config["PRECISE_CONCURRENT"]
    PRECISE_TIMEOUT = config["PRECISE_TIMEOUT"]
    SOCKS_PORT_START = config["SOCKS_PORT_START"]
    TEST_FILE_URL = config["TEST_FILE_URL"]

    # Загружаем российские CIDR
    russian_cidrs = await fetch_russian_cidrs_from_ripe()

    # Загружаем все ключи
    reality_uris = await download_all_vless_keys()
    total_reality = len(reality_uris)

    if total_reality == 0:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write("Скорость (Mbps),Пинг (мс),VLESS URI\n")
        save_vless_run_metadata(0, 0, 0, time.time() - start_time)
        return

    # Быстрая TCP-проверка
    semaphore_fast = asyncio.Semaphore(FAST_CONCURRENT)
    async def bounded_fast(uri):
        async with semaphore_fast:
            return uri, await fast_check_vless(uri)

    tasks_fast = [bounded_fast(uri) for uri in reality_uris]
    fast_results = await asyncio.gather(*tasks_fast)
    alive_uris = [uri for uri, ok in fast_results if ok]
    available_count = len(alive_uris)

    # Точная проверка
    valid_with_speed = []
    if alive_uris:
        semaphore_precise = asyncio.Semaphore(PRECISE_CONCURRENT)
        async def bounded_precise(uri, i):
            async with semaphore_precise:
                return uri, await precise_check_with_speed(uri, i, SOCKS_PORT_START + i)

        tasks_precise = [bounded_precise(uri, i) for i, uri in enumerate(alive_uris)]
        precise_results = await asyncio.gather(*tasks_precise)

        for uri, res in precise_results:
            if res:
                speed, ping = res
                valid_with_speed.append((uri, speed, ping))

        valid_with_speed.sort(key=lambda x: x[1], reverse=True)

    # Фильтрация: исключаем российские IP
    final_valid = []
    for uri, speed, ping in valid_with_speed:
        try:
            host = urlparse(uri).hostname
            if host and is_russian_ip_cached(host, russian_cidrs):
                continue
            final_valid.append((uri, speed, ping))
        except:
            final_valid.append((uri, speed, ping))

    working_non_russia = len(final_valid)

    # Сохраняем отчёт
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("Скорость (Mbps),Пинг (мс),VLESS URI\n")
        for uri, speed, ping in final_valid:
            f.write(f"{speed:.2f},{ping:.0f},{uri}\n")

    # Сохраняем метаданные
    duration_sec = time.time() - start_time
    save_vless_run_metadata(total_reality, available_count, working_non_russia, duration_sec)