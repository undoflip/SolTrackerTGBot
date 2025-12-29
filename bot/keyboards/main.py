from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(enabled: bool):
    emoji = "🟢" if enabled else "🔴"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Адреса", callback_data="menu:wallets")],
        [InlineKeyboardButton(text="🪙 Токены", callback_data="menu:tokens")],
        [InlineKeyboardButton(text=f"{emoji} Отслеживание", callback_data="toggle:user")]
    ])
