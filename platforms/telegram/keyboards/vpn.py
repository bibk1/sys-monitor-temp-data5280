# platforms/telegram/keyboards/vpn.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_vpn_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="VLESS", callback_data="vpn_vless")]
        ]
    )


def get_initial_vless_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔽 Показать ещё", callback_data="vpn_page:0")],
            [InlineKeyboardButton(text="✏️ Изменить источники", callback_data="vpn_edit_sources")],
            [InlineKeyboardButton(text="⚙️ Настройки проверки", callback_data="vpn_edit_config")],
            [InlineKeyboardButton(text="🇷🇺 Резервные CIDR", callback_data="vpn_edit_russian_cidrs")],
            [InlineKeyboardButton(text="🔄 Проверить VLESS-ключи", callback_data="vpn_check_vless")]
        ]
    )


def get_vless_page_keyboard(page: int, has_prev: bool, has_next: bool):
    buttons = []
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"vpn_page:{page - 1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="🔽 Ещё", callback_data=f"vpn_page:{page + 1}"))
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="✏️ Изменить источники", callback_data="vpn_edit_sources")])
    buttons.append([InlineKeyboardButton(text="⚙️ Настройки проверки", callback_data="vpn_edit_config")])
    buttons.append([InlineKeyboardButton(text="🇷🇺 Резервные CIDR", callback_data="vpn_edit_russian_cidrs")])
    buttons.append([InlineKeyboardButton(text="🔄 Проверить VLESS-ключи", callback_data="vpn_check_vless")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_edit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="vpn_cancel_edit")]
        ]
    )


def get_vpn_result_summary_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="VLESS", callback_data="vpn_vless")]
        ]
    )