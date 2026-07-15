# platforms/telegram/handlers/vpn.py
from aiogram import types
from aiogram.fsm.context import FSMContext
from datetime import datetime
import time
import os
import json
import ipaddress

# Импорты из модулей
from modules.vpn.actions_VLESS import (
    get_vless_uris_in_range,
    get_total_vless_count,
    run_vless_check,
    load_vless_run_metadata,
    SOURCES_FILE,
    CONFIG_FILE,
    load_vless_config,
    save_vless_config,
    RUSSIAN_CIDRS_FILE,
    load_russian_cidrs_fallback,
    save_russian_cidrs_fallback
)

# Состояния
from platforms.telegram.states.vpn import VPNStates

# Клавиатуры
from platforms.telegram.keyboards.vpn import (
    get_vpn_keyboard,
    get_cancel_edit_keyboard  # ← ЭТОТ ИМПОРТ ОБЯЗАТЕЛЕН
)


PAGE_SIZE = 10


def _format_vless_page(uris: list[tuple[str, str]], title: str = "🏆 Топ VLESS-серверов") -> str:
    if not uris:
        return "❌ Нет данных."
    lines = [f"{label}\n<code>{uri}</code>" for label, uri in uris]
    return f"{title}:\n\n" + "\n\n".join(lines)


async def show_vpn_menu(message: types.Message):
    from platforms.telegram.keyboards.vpn import get_vpn_keyboard
    await message.answer("🔑 Выберите действие:", reply_markup=get_vpn_keyboard())


async def show_vless_initial(callback: types.CallbackQuery):
    meta = load_vless_run_metadata()
    if meta:
        ts = datetime.fromisoformat(meta["timestamp"])
        dt_str = ts.strftime("%d.%m.%Y %H:%M")
        mins = int(meta["duration_sec"] // 60)
        secs = int(meta["duration_sec"] % 60)
        duration_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"

        stats = (
            f"🕒 Последняя проверка: {dt_str}\n"
            f"• Проверено REALITY-ключей: {meta['total_reality_keys']}\n"
            f"• Доступных REALITY-серверов: {meta['available_servers']}\n"
            f"• ✅ Рабочих с измеренной скоростью: {meta['working_servers']}\n"
            f"• ⏱️ Время выполнения: {duration_str}\n\n"
        )
    else:
        stats = "🕗 Нет данных о последней проверке.\n\n"

    uris = get_vless_uris_in_range(0, 3)
    if uris:
        key_lines = [f"{label}\n<code>{uri}</code>" for label, uri in uris]
        keys_section = "🏆 Топ VLESS-серверов:\n\n" + "\n\n".join(key_lines)
    else:
        keys_section = "❌ Нет рабочих ключей."

    text = stats + keys_section

    from platforms.telegram.keyboards.vpn import get_initial_vless_keyboard
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_initial_vless_keyboard(),
        disable_web_page_preview=True
    )
    await callback.answer()


async def show_vless_page(callback: types.CallbackQuery):
    try:
        page = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        page = 0

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    uris = get_vless_uris_in_range(start, end)

    total = get_total_vless_count()
    has_next = end < total
    has_prev = page > 0

    if page == 0:
        title = "🏆 Топ VLESS-серверов (1–10)"
    else:
        title = f"🏆 VLESS-серверы ({start + 1}–{min(end, total)})"

    text = _format_vless_page(uris, title)

    from platforms.telegram.keyboards.vpn import get_vless_page_keyboard
    keyboard = get_vless_page_keyboard(page, has_prev, has_next)

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback.answer()


async def handle_edit_sources(callback: types.CallbackQuery, state: FSMContext):
    if not os.path.exists(SOURCES_FILE):
        await callback.message.answer("❌ Файл источников не найден.")
        await callback.answer()
        return

    try:
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        await callback.message.answer(
            "📄 Текущие источники:\n\n"
            "<code>{}</code>\n\n"
            "Отправьте <b>новый список</b> (по одному URL на строку).\n"
            "Комментарии с <code>#</code> поддерживаются.\n\n"
            "⚠️ Нажмите «❌ Отмена», чтобы выйти.".format(content),
            parse_mode="HTML",
            reply_markup=get_cancel_edit_keyboard()
        )
        await state.set_state(VPNStates.waiting_for_sources)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка чтения: {e}")
    await callback.answer()


async def handle_new_sources(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != VPNStates.waiting_for_sources.state:
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение.")
        return

    try:
        with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
            f.write(message.text.strip())
        await message.answer("✅ Файл источников обновлён!")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка записи: {e}")


async def handle_edit_config(callback: types.CallbackQuery, state: FSMContext):
    config = load_vless_config()
    lines = []
    for key, value in config.items():
        lines.append(f"{key} = {repr(value)}")
    config_text = "\n".join(lines)

    await callback.message.answer(
        "⚙️ Текущие настройки проверки:\n\n"
        "<code>{}</code>\n\n"
        "Отправьте новые значения в формате:\n"
        "<code>КЛЮЧ = значение</code>\n"
        "Например:\n<code>FAST_CONCURRENT = 150</code>\n\n"
        "Поддерживаются типы: целые числа и строки.\n\n"
        "⚠️ Нажмите «❌ Отмена», чтобы выйти.".format(config_text),
        parse_mode="HTML",
        reply_markup=get_cancel_edit_keyboard()
    )
    await state.set_state(VPNStates.waiting_for_config)
    await callback.answer()


async def handle_new_config(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != VPNStates.waiting_for_config.state:
        return

    if not message.text:
        await message.answer("❌ Отправьте текст.")
        return

    config = load_vless_config()
    updated = False
    errors = []

    for line in message.text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " = " not in line:
            errors.append(f"Неверный формат: {line}")
            continue

        key, value_str = line.split(" = ", 1)
        key = key.strip()
        value_str = value_str.strip()

        if key not in config:
            errors.append(f"Неизвестный параметр: {key}")
            continue

        original_value = config[key]
        try:
            if isinstance(original_value, int):
                config[key] = int(value_str)
            elif isinstance(original_value, str):
                if value_str.startswith(("'", '"')) and value_str.endswith(("'", '"')):
                    config[key] = value_str[1:-1]
                else:
                    config[key] = value_str
            else:
                errors.append(f"Неподдерживаемый тип для {key}")
                continue
            updated = True
        except ValueError:
            errors.append(f"Неверное значение для {key}: {value_str}")

    if updated:
        save_vless_config(config)
        await message.answer("✅ Настройки обновлены!")
    if errors:
        await message.answer("⚠️ Ошибки:\n" + "\n".join(errors))
    
    await state.clear()


async def handle_edit_russian_cidrs(callback: types.CallbackQuery, state: FSMContext):
    cidrs = load_russian_cidrs_fallback()
    text = "🇷🇺 Текущие резервные CIDR:\n\n<code>{}</code>\n\n" \
           "Отправьте новый список (по одному CIDR на строку).\n" \
           "Пример:\n<code>5.136.0.0/13\n31.128.0.0/11</code>\n\n" \
           "⚠️ Нажмите «❌ Отмена», чтобы выйти.".format("\n".join(cidrs))
    
    from platforms.telegram.keyboards.vpn import get_cancel_edit_keyboard
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_edit_keyboard())
    await state.set_state(VPNStates.waiting_for_russian_cidrs)
    await callback.answer()


async def handle_new_russian_cidrs(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != VPNStates.waiting_for_russian_cidrs.state:
        return

    if not message.text:
        await message.answer("❌ Отправьте текст.")
        return

    cidrs = []
    errors = []
    for line in message.text.strip().splitlines():
        cidr = line.strip()
        if not cidr or cidr.startswith("#"):
            continue
        try:
            ipaddress.IPv4Network(cidr)
            cidrs.append(cidr)
        except Exception:
            errors.append(f"Неверный CIDR: {cidr}")

    if cidrs:
        save_russian_cidrs_fallback(cidrs)
        await message.answer("✅ Резервные CIDR обновлены!")
    if errors:
        await message.answer("⚠️ Ошибки:\n" + "\n".join(errors))
    
    await state.clear()


async def handle_cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Редактирование отменено.")
    await callback.answer()


async def start_vless_check(callback: types.CallbackQuery):
    await callback.message.answer("⏳ Запуск проверки VLESS-ключей...\nЭто может занять несколько минут.")
    await callback.answer()

    try:
        start_time = time.time()
        await run_vless_check()
        duration_sec = time.time() - start_time

        mins = int(duration_sec // 60)
        secs = int(duration_sec % 60)
        duration_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"

        total_working = get_total_vless_count()

        summary = (
            "✅ Проверка VLESS-ключей завершена!\n\n"
            "📊 Сводка:\n"
            "• Проверено REALITY-ключей: —\n"
            "• Доступных REALITY-серверов: —\n"
            f"• ✅ Рабочих с измеренной скоростью: {total_working}\n"
            f"• ⏱️ Время выполнения: {duration_str}"
        )

        from platforms.telegram.keyboards.vpn import get_vpn_result_summary_keyboard
        await callback.message.answer(
            summary,
            reply_markup=get_vpn_result_summary_keyboard()
        )

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при проверке:\n<code>{str(e)}</code>", parse_mode="HTML")