# handlers.py
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from bot.states import AddWallet, AddToken
from bot.keyboards import wallets_menu, main_menu, tokens_menu

from sqlalchemy import select, update
from sqlalchemy import func

from db.models import User, Wallet, Token
from db.engine import AsyncSession

from solana_tracker.parser import get_token_metadata
from config import TOKEN_SYMBOLS

from loguru import logger


router = Router()

# command /start
@router.message(CommandStart())
async def start_handler(message: Message):
    logger.info(f"User {message.from_user.id} started the bot.")

    async with AsyncSession() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == message.from_user.id)
        )

        if not user:
            user = User(
                telegram_id=message.from_user.id,
                enabled=True
            )
            session.add(user)
            await session.commit()
            logger.success(f"Created new user {message.from_user.id}.")

            for token_address in TOKEN_SYMBOLS:
                token_symbol = TOKEN_SYMBOLS[token_address]

                token = Token(
                user_id=user.id,
                mint=token_address,
                symbol="SOL" if token_symbol == "WSOL" else token_symbol,
                enabled=True
                )
        
                session.add(token)
            await session.commit()
            logger.success(f"Added default tokens for user {message.from_user.id}.")

    await message.answer(
        "Главное меню",
        reply_markup=main_menu(user.enabled)
    )

# Menu
@router.callback_query(F.data == "menu:wallets")
async def wallets_menu_handler(cb: CallbackQuery):
    async with AsyncSession() as session:
        wallets = (await session.execute(
            select(Wallet).join(User).where(
                User.telegram_id == cb.from_user.id
            )
        )).scalars().all()

    await cb.message.edit_text(
        "Отслеживаемые адреса",
        reply_markup=wallets_menu(wallets)
    )

@router.callback_query(F.data == "menu:tokens")
async def tokens_menu_handler(cb: CallbackQuery):
    async with AsyncSession() as session:
        tokens = (await session.execute(
            select(Token).join(User).where(
                User.telegram_id == cb.from_user.id
            )
        )).scalars().all()

    await cb.message.edit_text(
        "Отслеживаемые токены",
        reply_markup=tokens_menu(tokens)
    )

@router.callback_query(F.data == "menu:main")
async def back_to_main(cb: CallbackQuery):
    async with AsyncSession() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == cb.from_user.id)
        )

    await cb.message.edit_text(
        "Главное меню",
        reply_markup=main_menu(user.enabled)
    )

# Wallets
@router.callback_query(F.data.startswith("toggle:wallet:"))
async def toggle_wallet(cb: CallbackQuery):
    wallet_id = int(cb.data.split(":")[2])

    async with AsyncSession() as session:
        wallet = await session.get(Wallet, wallet_id)
        wallet.enabled = not wallet.enabled
        await session.commit()
        logger.info(f"Toggled wallet {wallet_id} to {wallet.enabled}")

    await cb.answer("Готово")
    await wallets_menu_handler(cb)

@router.callback_query(F.data.in_(["wallets:on", "wallets:off"]))
async def toggle_all_wallets(cb: CallbackQuery):
    value = cb.data.endswith("on")

    async with AsyncSession() as session:
        await session.execute(
            update(Wallet)
            .where(Wallet.user_id == User.id)
            .where(User.telegram_id == cb.from_user.id)
            .values(enabled=value)
        )
        await session.commit()
        logger.info(f"Set all wallets for user {cb.from_user.id} to {value}")

    await cb.answer("Готово")
    await wallets_menu_handler(cb)


@router.callback_query(F.data == "add:wallet")
async def add_wallet_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddWallet.waiting_for_input)
    await cb.message.edit_text(
        "Отправь адрес и название через `;`, например:\n"
        "`GrQdkm...abc; Мой кошелек`"
    )

@router.message(AddWallet.waiting_for_input)
async def add_wallet_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if ";" not in text:
        await msg.answer("❌ Формат неверный. Используй `адрес; label`")
        return

    address, label = map(str.strip, text.split(";", 1))

    if len(address) < 32:
        await msg.answer("❌ Адрес слишком короткий")
        return

    async with AsyncSession() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == msg.from_user.id)
        )

        # 🔍 Проверяем, есть ли уже такой label
        exists_label = await session.scalar(
        select(Wallet).where(
            Wallet.user_id == user.id,
            func.lower(Wallet.label) == label.lower()
        )
    )

        if exists_label:
            await msg.answer("❌ Этот label уже используется")
            return

        # 🔍 Проверяем, есть ли уже такой адрес
        exists_address = await session.scalar(
            select(Wallet).where(
                Wallet.user_id == user.id,
                Wallet.address == address
            )
        )
        
        if exists_address:
            await msg.answer("❌ Этот адрес уже добавлен")
            return

        wallet = Wallet(
            user_id=user.id,
            address=address,
            label=label,
            enabled=True
        )
        session.add(wallet)
        await session.commit()
        logger.info(f"Added wallet {address} for user {msg.from_user.id}")

    await state.clear()
    await msg.answer(
        f"✅ Адрес `{address}` с меткой `{label}` добавлен",
        reply_markup=main_menu(user.enabled)
    )

# Tokens
@router.callback_query(F.data.startswith("toggle:token:"))
async def toggle_token(cb: CallbackQuery):
    token_id = int(cb.data.split(":")[2])

    async with AsyncSession() as session:
        token = await session.get(Token, token_id)
        token.enabled = not token.enabled
        await session.commit()

    await cb.answer("Готово")
    await tokens_menu_handler(cb)

@router.callback_query(F.data.in_(["tokens:on", "tokens:off"]))
async def toggle_all_tokens(cb: CallbackQuery):
    value = cb.data.endswith("on")

    async with AsyncSession() as session:
        await session.execute(
            update(Token)
            .where(Token.user_id == User.id)
            .where(User.telegram_id == cb.from_user.id)
            .values(enabled=value)
        )
        await session.commit()
        logger.info(f"Set all tokens for user {cb.from_user.id} to {value}")

    await cb.answer("Готово")
    await tokens_menu_handler(cb)


@router.callback_query(F.data == "add:token")
async def add_token_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddToken.waiting_for_input)
    await cb.message.edit_text(
        "Отправь адрес адрес токена формата: GrQdkm...abc"
    )

@router.message(AddToken.waiting_for_input)
async def add_token_input(msg: Message, state: FSMContext):
    address = msg.text.strip()

    if len(address) < 32:
        await msg.answer("❌ Адрес слишком короткий")
        return

    async with AsyncSession() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == msg.from_user.id)
        )

        # 🔍 Проверяем, есть ли уже такой адрес
        exists = await session.scalar(
            select(Token).where(
                Token.user_id == user.id,
                Token.mint == address
            )
        )

        if exists:
            await msg.answer("❌ Этот токен уже добавлен")
            return
        
        token_name = await get_token_metadata(address)
        if token_name is None:
            await msg.answer("❌ Не удалось получить метаданные токена. Проверь адрес.")
            return

        token = Token(
            user_id=user.id,
            mint=address,
            symbol=token_name,
            enabled=True
        )
        session.add(token)
        await session.commit()

    await state.clear()
    await msg.answer(
        f"✅ Token `{token_name}` добавлен",
        reply_markup=main_menu(user.enabled)
    )

# All switch user enable/disable
@router.callback_query(F.data == "toggle:user")
async def toggle_user(cb: CallbackQuery):
    async with AsyncSession() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == cb.from_user.id)
        )
        user.enabled = not user.enabled
        await session.commit()

    await cb.answer("Переключено")
    await cb.message.edit_text(
        "Главное меню",
    reply_markup=main_menu(user.enabled)
)

