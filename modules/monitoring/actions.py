# modules/monitoring/actions.py
import psutil
import subprocess
import os
import time

# Глобальное состояние для расчёта мощности (как в оригинале)
_CPU_POWER_STATE = {"energy_uj": None, "timestamp": None}

def get_system_info():
    """Возвращает структурированные данные о системе."""
    cpu = _get_detailed_cpu_info()
    ram = _get_memory_info()
    disk = _get_disk_info("/")
    net_interface = _get_main_network_interface()
    net_io = _get_net_io(net_interface) if net_interface else None
    disk_io = _get_disk_io()
    swap = _get_swap_info()

    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "swap": swap,
        "network": {
            "interface": net_interface,
            "io": net_io
        },
        "disk_io": disk_io
    }

# --- Внутренние функции (аналог system_info.py) ---

def _get_detailed_cpu_info():
    cores_load = psutil.cpu_percent(interval=0.5, percpu=True)
    cores_freq = []
    freqs = psutil.cpu_freq(percpu=True)
    if freqs:
        cores_freq = [f.current for f in freqs]

    temps = {"package_temp": None, "core_temps": []}
    sensors = psutil.sensors_temperatures()
    if sensors:
        for name, entries in sensors.items():
            if 'coretemp' in name:
                for entry in entries:
                    if 'Package' in entry.label or 'Tdie' in entry.label or 'Tctl' in entry.label:
                        temps["package_temp"] = entry.current
                    elif 'Core' in entry.label:
                        temps["core_temps"].append(entry.current)
            elif 'k10temp' in name or 'zenpower' in name:
                for entry in entries:
                    if 'Tdie' in entry.label or 'Tctl' in entry.label:
                        temps["package_temp"] = entry.current
                    elif 'Core' in entry.label:
                        temps["core_temps"].append(entry.current)

    return {
        "cores_load": cores_load,
        "cores_freq": cores_freq,
        "package_temp": temps["package_temp"],
        "core_temps": temps["core_temps"],
        "power_w": _get_cpu_power_watts()
    }

def _get_memory_info():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 1),
        "used_gb": round(mem.used / (1024 ** 3), 1),
        "percent": mem.percent
    }

def _get_swap_info():
    swap = psutil.swap_memory()
    if swap.total == 0:
        return {"exists": False}
    return {
        "exists": True,
        "total_gb": round(swap.total / (1024 ** 3), 1),
        "used_gb": round(swap.used / (1024 ** 3), 1),
        "percent": swap.percent
    }

def _get_disk_info(path="/"):
    usage = psutil.disk_usage(path)
    disk_info = {
        "total_gb": round(usage.total / (1024 ** 3), 1),
        "used_gb": round(usage.used / (1024 ** 3), 1),
        "percent": usage.percent,
        "temp_c": None
    }

    try:
        result = subprocess.run(['df', path], capture_output=True, text=True, timeout=2)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            device = lines[1].split()[0]
            base_device = device.split('p')[0] if 'nvme' in device and 'p' in device else ''.join([c for c in device if not c.isdigit()])
            if os.path.exists(base_device):
                smart = subprocess.run(
                    ['sudo', 'smartctl', '-A', base_device],
                    capture_output=True, text=True, timeout=3
                )
                if smart.returncode == 0:
                    for line in smart.stdout.split('\n'):
                        if 'Temperature_Celsius' in line or 'Airflow_Temperature' in line:
                            parts = line.split()
                            if len(parts) >= 10 and parts[9].isdigit():
                                disk_info["temp_c"] = int(parts[9])
                                break
    except Exception:
        pass

    return disk_info

def _get_main_network_interface():
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    for iface, addr_list in addrs.items():
        if iface == "lo" or not stats.get(iface):
            continue
        has_ipv4 = any(a.family == 2 and a.address != "127.0.0.1" for a in addr_list)
        if has_ipv4:
            return iface
    return None

def _get_net_io(interface):
    try:
        counters = psutil.net_io_counters(pernic=True)[interface]
        return {
            "bytes_recv": counters.bytes_recv,
            "bytes_sent": counters.bytes_sent
        }
    except Exception:
        return None

def _get_disk_io():
    try:
        io = psutil.disk_io_counters()
        if io:
            return {
                "read_bytes": io.read_bytes,
                "write_bytes": io.write_bytes
            }
    except Exception:
        pass
    return None

# --- Power monitoring ---
def _get_cpu_energy_uj():
    rapl_dir = "/sys/class/powercap"
    if not os.path.exists(rapl_dir):
        return None
    for domain in sorted(os.listdir(rapl_dir)):
        if (domain.startswith("intel-rapl") and ":" not in domain) or domain.startswith("amd-rapl"):
            energy_path = os.path.join(rapl_dir, domain, "energy_uj")
            if os.path.isfile(energy_path):
                try:
                    with open(energy_path, "r") as f:
                        return int(f.read().strip())
                except Exception:
                    continue
    return None

def _get_cpu_power_watts():
    global _CPU_POWER_STATE
    current_energy = _get_cpu_energy_uj()
    current_time = time.time()

    if current_energy is None:
        return None

    prev_energy = _CPU_POWER_STATE["energy_uj"]
    prev_time = _CPU_POWER_STATE["timestamp"]

    power_w = None
    if prev_energy is not None and prev_time is not None:
        delta_energy_j = (current_energy - prev_energy) / 1_000_000
        delta_time_s = current_time - prev_time
        if delta_time_s > 0.1:
            power_w = delta_energy_j / delta_time_s

    _CPU_POWER_STATE["energy_uj"] = current_energy
    _CPU_POWER_STATE["timestamp"] = current_time
    return power_w