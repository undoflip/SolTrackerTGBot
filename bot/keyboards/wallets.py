from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def wallets_menu(wallets):
    kb = []

    for w in wallets:
        emoji = "🟢" if w.enabled else "🔴"
        kb.append([
            InlineKeyboardButton(
                text=f"{emoji} {w.label}",
                callback_data=f"toggle:wallet:{w.id}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
        text="➕ Добавить адрес",
        callback_data="add:wallet"
    )
    ])
    kb.append([
        InlineKeyboardButton(text="🟢 Включить все", callback_data="wallets:on"),
        InlineKeyboardButton(text="🔴 Выключить все", callback_data="wallets:off"),
    ])
    kb.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="menu:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)
