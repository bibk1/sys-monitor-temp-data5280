# platforms/telegram/handlers/systemd.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import asyncio

from modules.systemd.config_loader import load_services, get_service_by_id, toggle_service_autostart
from modules.systemd.actions import (
    get_service_status, perform_action, check_sudo_permissions
)
import os
from modules.systemd.config_loader import CONFIG_FILE as SYSTEMD_CONFIG_FILE

from platforms.telegram.states.systemd import SystemdStates
from platforms.telegram.keyboards.systemd import (
    get_services_list_keyboard, get_service_control_keyboard,
    get_logs_keyboard, get_confirm_keyboard, get_cancel_edit_keyboard
)

router = Router()
PAGE_SIZE = 5

async def get_fresh_services_data():
    services = load_services()
    items = []
    for svc in services:
        status = await get_service_status(svc)
        items.append({'id': svc.id, 'name': svc.name, 'status': status})
    return items

async def send_or_edit_list(message: types.Message, items: list, page: int, text_prefix: str = ""):
    total = len(items)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]
    has_prev = page > 0
    has_next = end < total
    
    text = f"⚙️ **Systemd службы** (Стр. {page+1})\n\n"
    if text_prefix: text += f"{text_prefix}\n\n"
    if not page_items: text += "Нет сервисов."
    
    kb = get_services_list_keyboard(page_items, page, has_next, has_prev)
    
    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except TelegramBadRequest:
        try: await message.delete()
        except: pass
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")

async def refresh_and_show_list(message: types.Message, notification_text: str):
    items = await get_fresh_services_data()
    await send_or_edit_list(message, items, 0, text_prefix=notification_text)

async def check_permissions_message(message: types.Message):
    ok, msg = await check_sudo_permissions()
    if not ok:
        await message.answer(f"⚠️ **Ошибка прав:**\n{msg}", parse_mode="Markdown")
        return False
    return True

@router.callback_query(F.data == "sysd_main")
async def show_systemd_main(callback: types.CallbackQuery):
    if not await check_permissions_message(callback.message): return
    items = await get_fresh_services_data()
    if not items:
        await callback.message.edit_text("❌ Список пуст.")
        return
    await send_or_edit_list(callback.message, items, 0)
    await callback.answer()

@router.callback_query(F.data.startswith("sysd_page:"))
async def handle_page_change(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    items = await get_fresh_services_data()
    await send_or_edit_list(callback.message, items, page)
    await callback.answer()

@router.callback_query(F.data.startswith("sysd_list:"))
async def back_to_list(callback: types.CallbackQuery):
    items = await get_fresh_services_data()
    await send_or_edit_list(callback.message, items, 0)
    await callback.answer()

@router.callback_query(F.data.startswith("sysd_svc:"))
async def handle_service_select(callback: types.CallbackQuery, state: FSMContext):
    service_id = callback.data.split(":")[1]
    service = get_service_by_id(service_id)
    if not service:
        await callback.answer("❌ Не найден", show_alert=True); return
    
    status_text = await get_service_status(service)
    is_auto = service.autostart
    
    kb = get_service_control_keyboard(service.id, service.name, is_auto)
    text = f"🛠 **{service.name}**\n_Desc:_ {service.description}\n\n📊 **Статус:**\n{status_text}"
    
    await state.clear()
    try: await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except TelegramBadRequest: await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("sysd_act:"))
async def handle_action(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    service_id, action = parts[1], parts[2]
    service = get_service_by_id(service_id)
    if not service: await callback.answer("❌ Ошибка", show_alert=True); return

    if action in ["restart", "stop"]:
        kb = get_confirm_keyboard(service_id, action)
        try: await callback.message.edit_reply_markup(reply_markup=kb)
        except: pass
        await callback.answer(); return

    await callback.answer("⏳ Выполнение...")
    success, result_msg = await perform_action(service, action)
    icon = "✅" if success else "❌"
    
    if action == "logs":
        await state.set_state(SystemdStates.viewing_logs)
        await callback.message.answer(f"📜 **Логи**:\n<code>{result_msg}</code>", reply_markup=get_logs_keyboard(service_id), parse_mode="HTML")
    else:
        await asyncio.sleep(1.5)
        await refresh_and_show_list(callback.message, f"{icon} {service.name}: {result_msg}")

@router.callback_query(F.data.startswith("sysd_confirmed:"))
async def handle_confirmed_action(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    service_id, action = parts[1], parts[2]
    service = get_service_by_id(service_id)
    if not service: await callback.answer("❌ Ошибка", show_alert=True); return

    await callback.answer("⏳ Выполнение...")
    success, result_msg = await perform_action(service, action)
    icon = "✅" if success else "❌"
    await asyncio.sleep(1.5)
    await refresh_and_show_list(callback.message, f"{icon} {service.name}: {result_msg}")

# --- Editing Handlers (Только services.yaml) ---

@router.callback_query(F.data == "sysd_edit_config")
async def handle_edit_services_yaml(callback: types.CallbackQuery, state: FSMContext):
    try:
        with open(SYSTEMD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True); return
        
    if len(content) > 4000: await callback.message.answer("⚠️ Слишком большой файл."); await callback.answer(); return

    text = f"⚙️ **Systemd services.yaml**\n<code>{content}</code>\n\n✏️ Отправьте новый текст."
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_edit_keyboard())
    # Используем состояние editing_compose из DockerStates или создаем общее, 
    # но для простоты используем любое свободное или создадим новое в SystemdStates если нужно.
    # Для единообразия оставим логику похожей, но без привязки к конкретному сервису
    await state.set_state(SystemdStates.viewing_logs) # Временно используем это состояние как флаг редактирования
    await state.update_data(editing_target="services_yaml")
    await callback.answer()

@router.callback_query(F.data == "sysd_cancel_edit")
async def handle_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try: await callback.message.delete()
    except: pass
    await callback.answer("Отменено.")

@router.message(SystemdStates.viewing_logs) # Перехватываем сообщение в этом состоянии для редактирования
async def process_new_content(message: types.Message, state: FSMContext):
    if not message.text: return
    data = await state.get_data()
    target = data.get("editing_target")
    
    if target != "services_yaml":
        return # Игнорируем, если это не режим редактирования конфига

    await message.answer("⏳ Сохранение...")
    
    try:
        with open(SYSTEMD_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(message.text)
        await message.answer(f"✅ Конфигурация обновлена.\nПерезайдите в меню.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()

@router.callback_query(F.data == "sysd_back_menu")
async def back_to_main(callback: types.CallbackQuery):
    from platforms.telegram.keyboards.main_menu import get_main_menu_keyboard
    try: await callback.message.edit_text("👋 Меню:", reply_markup=get_main_menu_keyboard())
    except TelegramBadRequest: await callback.message.answer("👋 Меню:", reply_markup=get_main_menu_keyboard())
    await callback.answer()