# platforms/telegram/handlers/monitoring.py
from aiogram import types
from modules.monitoring.actions import get_system_info
from platforms.telegram.keyboards.monitoring import get_monitoring_keyboard

# Вспомогательные функции форматирования (как в оригинале)
def _format_optional(value, unit="") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.1f}{unit}"
    return f"{value}{unit}"

def _format_bytes(bytes_val: int) -> str:
    if bytes_val == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"

def _format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec == 0:
        return "0 B/s"
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024
    return f"{bytes_per_sec:.1f} TB/s"

async def show_monitoring(message: types.Message):
    data = get_system_info()
    msg = _build_system_message(data)
    await message.answer(msg, parse_mode="HTML", reply_markup=get_monitoring_keyboard())

async def refresh_monitoring(callback_query: types.CallbackQuery):
    data = get_system_info()
    msg = _build_system_message(data)
    await callback_query.message.edit_text(msg, parse_mode="HTML", reply_markup=get_monitoring_keyboard())
    await callback_query.answer()

async def back_to_main(callback_query: types.CallbackQuery):
    from platforms.telegram.keyboards.main_menu import get_main_menu_keyboard
    await callback_query.message.edit_text("Выберите действие:", reply_markup=get_main_menu_keyboard())
    await callback_query.answer()

def _build_system_message(data) -> str:
    cpu = data["cpu"]
    ram = data["ram"]
    disk = data["disk"]
    swap = data["swap"]
    net = data["network"]
    disk_io = data["disk_io"]

    msg = "🖥️ <b>Мониторинг системы</b>\n\n"

    # CPU
    avg_load = sum(cpu["cores_load"]) / len(cpu["cores_load"])
    msg += f"🔹 <b>CPU</b>\n• Общая загрузка: {avg_load:.1f}%\n"
    msg += f"• Package температура: {_format_optional(cpu['package_temp'], '°C')}\n"
    if cpu["power_w"] is not None:
        msg += f"• Потребление: {cpu['power_w']:.1f} Вт\n"
    else:
        msg += "• Потребление: недоступно\n"
    msg += "• По ядрам:\n"
    for i, load in enumerate(cpu["cores_load"]):
        freq = cpu["cores_freq"][i] if i < len(cpu["cores_freq"]) else None
        temp = cpu["core_temps"][i] if i < len(cpu["core_temps"]) else None
        msg += f"  Core {i}: {load:.1f}% @ {_format_optional(freq, ' MHz')} ({_format_optional(temp, '°C')})\n"

    # RAM
    msg += f"\n🧠 <b>ОЗУ</b>\n• Загрузка: {ram['used_gb']}/{ram['total_gb']} ГБ ({ram['percent']}%)\n"

    # Swap
    msg += "\n🔄 <b>Подкачка (Swap)</b>\n"
    if swap["exists"]:
        msg += f"• Размер: {swap['used_gb']}/{swap['total_gb']} ГБ ({swap['percent']:.1f}%)\n"
    else:
        msg += "• Файл подкачки отсутствует\n"

    # Disk
    msg += f"\n💾 <b>Диск (/)</b>\n• Загрузка: {disk['used_gb']}/{disk['total_gb']} ГБ ({disk['percent']}%)\n"
    msg += f"• Температура: {_format_optional(disk['temp_c'], '°C')}\n"

    # Disk I/O (упрощённо — без динамики скорости, т.к. нет контекста)
    if disk_io:
        msg += f"• Чтение всего: {_format_bytes(disk_io['read_bytes'])}\n"
        msg += f"• Запись всего: {_format_bytes(disk_io['write_bytes'])}\n"

    # Network
    msg += "\n🌐 <b>Сеть</b>\n"
    if net["interface"]:
        io = net["io"]
        if io:
            msg += f"• Интерфейс: <code>{net['interface']}</code>\n"
            msg += f"• Приём всего: {_format_bytes(io['bytes_recv'])}\n"
            msg += f"• Отправка всего: {_format_bytes(io['bytes_sent'])}\n"
        else:
            msg += f"• Интерфейс: <code>{net['interface']}</code> (статистика недоступна)\n"
    else:
        msg += "• Статус: ❌ Нет активного подключения\n"

    return msg