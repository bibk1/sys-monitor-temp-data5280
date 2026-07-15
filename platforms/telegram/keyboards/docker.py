# platforms/telegram/keyboards/docker.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

def get_services_list_keyboard(services_: List[dict], page: int, has_next: bool, has_prev: bool):
    keyboard = []
    for item in services_:
        status = item.get('status', '')
        if "🟢" in status: status_icon = "🟢"
        elif "🟡" in status: status_icon = "🟡"
        elif "🔴" in status: status_icon = "🔴"
        else: status_icon = "⚪"
            
        text = f"{status_icon} {item['name']}"
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"dock_svc:{item['id']}")])
    
    nav_row = []
    if has_prev: nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"dock_page:{page-1}"))
    if has_next: nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"dock_page:{page+1}"))
    if nav_row: keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton(text="⚙️ Редактировать services.yaml", callback_data="dock_edit_config")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_service_control_keyboard(service_id: str, service_name: str, is_auto_enabled: bool):
    auto_icon = "🟢" if is_auto_enabled else "🔴"
    auto_status_text = "ВКЛ" if is_auto_enabled else "ВЫКЛ"
    auto_action = "disable_auto" if is_auto_enabled else "enable_auto"
    
    keyboard = [
        [
            InlineKeyboardButton(text="▶️ Старт", callback_data=f"dock_act:{service_id}:start"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data=f"dock_act:{service_id}:stop")
        ],
        [
            InlineKeyboardButton(text="🔄 Рестарт", callback_data=f"dock_act:{service_id}:restart")
        ],
        [InlineKeyboardButton(text="📜 Логи (50 строк)", callback_data=f"dock_act:{service_id}:logs")],
        [InlineKeyboardButton(text="📝 Редактировать docker-compose.yml", callback_data=f"dock_edit:{service_id}")],
        [InlineKeyboardButton(text=f"{auto_icon} Автозапуск: {auto_status_text}", callback_data=f"dock_act:{service_id}:{auto_action}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="dock_list:0")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="dock_cancel_edit")]
    ])

def get_logs_keyboard(service_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить логи", callback_data=f"dock_act:{service_id}:logs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"dock_svc:{service_id}")]
    ])

def get_confirm_keyboard(service_id: str, action: str):
    action_names = {"restart": "перезагрузку", "stop": "остановку"}
    act_name = action_names.get(action, action)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Подтвердить {act_name}", callback_data=f"dock_confirmed:{service_id}:{action}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"dock_svc:{service_id}")]
    ])