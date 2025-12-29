# workers/solana_worker.py
import asyncio
from solana_tracker import parse_transaction
from utils import semaphore
from loguru import logger
from bot import bot
from config import config
from db.models import User, Wallet, Token
from db.engine import AsyncSession
from sqlalchemy import select, func

def short(addr: str, n=4):
    return f"{addr[:n]}...{addr[-n:]}"


async def tx_worker(queue: asyncio.Queue, client):
    while True:
        signature, wallet = await queue.get()
        try:
            async with semaphore:
                parsed_transaction = await parse_transaction(signature, wallet, client)

            if parsed_transaction:
                for whitelist_user in config.whitelisted_user_ids:
                    async with AsyncSession() as session:
                        user = await session.scalar(
                            select(User).where(User.telegram_id == whitelist_user)
                        )
                        if not user.enabled:
                            logger.info(f"User {whitelist_user} is disabled. Skipping notification.")    
                            continue

                        user_wallet = await session.scalar(
                            select(Wallet).where(Wallet.user_id == user.id,
                                                 func.lower(Wallet.address) == parsed_transaction['wallet'].lower())
                        )
                        if not user_wallet:
                            # logger.info(f"Wallet {parsed_transaction['wallet']} not found for user {whitelist_user}. Skipping notification.")
                            continue

                        if not user_wallet.enabled:
                            logger.info(f"User {whitelist_user} is disabled. Skipping notification.")    
                            continue
                        sent_token_symbol = "SOL" if parsed_transaction['sent_symbol'] == "WSOL" else parsed_transaction['sent_symbol']
                        user_token = await session.scalar(
                            select(Token).where(Token.user_id == user.id,
                                                func.lower(Token.symbol) == sent_token_symbol.lower())
                        )

                        if parsed_transaction['side'] == "TRANSFER":
                            if user_token:
                                if user_token.enabled:
                                    await bot.send_message(
                                        chat_id=user.telegram_id,
                                        parse_mode="HTML",
                                        text=(
                                            f"📤 <b>TRANSFER</b>\n\n"
                                            f"👛 <b>Wallet:</b> {user_wallet.label}\n"
                                            f"📦 <b>Amount:</b> {parsed_transaction['sent_amount']:.6f} {sent_token_symbol}\n"
                                            f"➡️ <b>To:</b> <code>{short(parsed_transaction['to_address'])}</code>\n\n"
                                            f"🔗 <a href='https://solscan.io/tx/{signature}'>View on Solscan</a>"
                                        )
                                    )
                                    logger.success(
                                        f"[{parsed_transaction['wallet']}] {parsed_transaction['side']} "
                                        f"{parsed_transaction['sent_amount']:.6f} {sent_token_symbol} "
                                        f"to [{parsed_transaction['to_address']}]"
                                        f" | {user_wallet.label} >>> https://solscan.io/tx/{signature} |"
                                    )
                        elif parsed_transaction['side'] == "SKIPPED":
                            await bot.send_message(
                                chat_id=user.telegram_id,
                                parse_mode="HTML",
                                text=(
                                    f"⚠️ <b>TRANSACTION SKIPPED</b>\n\n"
                                    f"👛 <b>Wallet:</b> {user_wallet.label}\n"
                                    f"📝 <b>Description:</b>\n"
                                    f"<i>{parsed_transaction['description']}</i>\n\n"
                                    f"🔎 <a href='https://solscan.io/tx/{signature}'>Check on Solscan</a>"
                                )
                            )
                            logger.warning(
                                f" <b>Transaction</b> [{parsed_transaction['signature']}] {parsed_transaction['side']}\n"
                                f"📤 <b>Sent:</b> {parsed_transaction['sent_amount']:.6f} {sent_token_symbol}\n"
                                f"🔗 <b>Description:</b> {parsed_transaction['description']}" + " -- Check this tx manually for details."
                                f"| {user_wallet.label} >>> https://solscan.io/tx/{signature} |"
                            )
                        elif parsed_transaction['side'] == "SWAP":
                            recv_token_symbol = "SOL" if parsed_transaction['recv_symbol'] == "WSOL" else parsed_transaction['recv_symbol']
                            if user_token:
                                if user_token.enabled:
                                    await bot.send_message(
                                        chat_id=user.telegram_id,
                                        parse_mode="HTML",
                                        text=(
                                            f"💱 <b>SWAP</b>\n\n"
                                            f"👛 <b>Wallet:</b> {user_wallet.label}\n"
                                            f"📤 <b>Sent:</b> {parsed_transaction['sent_amount']:.6f} {sent_token_symbol}\n"
                                            f"📥 <b>Received:</b> {parsed_transaction['recv_amount']:.9f} {recv_token_symbol}\n"
                                            f"🔄 <b>DEX:</b> {parsed_transaction['aggregator']}\n\n"
                                            f"🔗 <a href='https://solscan.io/tx/{signature}'>View on Solscan</a>"
                                        )
                                    )
                                    logger.success(
                                        f"[{parsed_transaction['side']}] "
                                        f"{parsed_transaction['sent_amount']:.6f} {sent_token_symbol} → "
                                        f"{parsed_transaction['recv_amount']:.9f} {recv_token_symbol} "
                                        f"({parsed_transaction['aggregator']}))"
                                        f"| {user_wallet.label} >>> https://solscan.io/tx/{signature} |"
                                    )

        except Exception as e:
            logger.error(f"❌ {signature}: {type(e).__name__} {e}")

        finally:
            queue.task_done()
