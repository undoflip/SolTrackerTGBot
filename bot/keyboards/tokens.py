from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def tokens_menu(tokens):
    kb = []

    for token in tokens:
        emoji = "🟢" if token.enabled else "🔴"
        kb.append([
            InlineKeyboardButton(
                text=f"{emoji} {token.symbol}",
                callback_data=f"toggle:token:{token.id}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
        text="➕ Добавить токен",
        callback_data="add:token"
    )
    ])
    kb.append([
        InlineKeyboardButton(text="🟢 Включить все", callback_data="tokens:on"),
        InlineKeyboardButton(text="🔴 Выключить все", callback_data="tokens:off"),
    ])
    kb.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="menu:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)
