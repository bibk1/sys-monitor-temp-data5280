# modules/network/actions.py
import subprocess
import socket
import re
import requests
import psutil
from pathlib import Path


def get_wifi_ssid() -> str:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "GENERAL.CONNECTION", "device", "show", "wlp2s0"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            conn_name = result.stdout.strip().split(":", 1)[-1].strip()
            if conn_name and conn_name != "--":
                ssid_result = subprocess.run(
                    ["nmcli", "-g", "802-11-wireless.ssid", "con", "show", conn_name],
                    capture_output=True, text=True, timeout=3
                )
                if ssid_result.returncode == 0:
                    ssid = ssid_result.stdout.strip()
                    if ssid:
                        return ssid
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["wpa_cli", "status"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("ssid="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass

    return "❓ Неизвестно"


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Нет подключения"


def get_default_gateway() -> str:
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=2
        )
        match = re.search(r"via\s+([0-9.]+)", result.stdout)
        return match.group(1) if match else "Неизвестен"
    except Exception:
        return "Недоступен"


def get_mac_address() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        for iface_name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == local_ip:
                    for addr2 in addrs:
                        if addr2.family == psutil.AF_LINK:
                            return addr2.address.upper()
        return "Неизвестен"
    except Exception:
        return "Ошибка"


def get_external_ip() -> str:
    try:
        response = requests.get("https://ifconfig.me/ip", timeout=5)
        if response.status_code == 200:
            ip = response.text.strip()
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
                return ip
        return "❌ Ошибка"
    except Exception:
        return "❌ Недоступен"


def check_internet_http() -> str:
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return "✅ Доступен" if response.status_code == 200 else "⚠️ Ограничен"
    except Exception:
        return "❌ Недоступен"


def ping_host(host: str = "8.8.8.8", count: int = 3) -> str:
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            match = re.search(r"=.*?/([0-9.]+)/", result.stdout)
            if match:
                return f"{match.group(1)} мс"
        return "❌ Недоступен"
    except Exception:
        return "❌ Ошибка"


def get_network_info() -> dict:
    """Возвращает сетевую информацию БЕЗ VPN."""
    return {
        "ssid": get_wifi_ssid(),
        "local_ip": get_local_ip(),
        "gateway": get_default_gateway(),
        "mac_address": get_mac_address(),
        "external_ip": get_external_ip(),
        "internet_status": check_internet_http(),
        "ping": ping_host(),
    }