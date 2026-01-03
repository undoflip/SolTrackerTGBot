# solana_tracker/parser.py
import httpx
from inspect import signature
from collections import defaultdict

from config import config, TOKEN_SYMBOLS, AGGREGATORS
from loguru import logger

from db.models import Token
from db.engine import AsyncSession
from sqlalchemy import select, func

HELIUS_URL = "https://api-mainnet.helius-rpc.com/v0/transactions/"

async def parse_transaction(signature: str, wallet: str, client: httpx.AsyncClient):
    resp = await client.post(
        HELIUS_URL,
        params={"api-key": config.helius_api_key},
        json={"transactions": [signature]}
    )

    if resp.status_code != 200:
        logger.error(f"Helius returned {resp.status_code} for tx {signature}")
        return None

    data = resp.json()
    if not data:
        logger.error(f"No data returned from Helius API for tx {signature}, skipping all them!")
        return None

    tx = data[0]
    # print(tx)
    tx_type = tx.get("type")
    source = tx.get("source")
    if tx_type == "UNKNOWN":
        tx_type = "SWAP"
    if tx.get('fee') > 8000 and (tx_type == "TRANSFER" or source == "SYSTEM_PROGRAM"):
        tx_type = "SWAP"
        source = "JUPITER"
    
    first_transfer_dict = tx["tokenTransfers"][0]
    sent_mint = first_transfer_dict['mint']
    sent_symbol = await get_token_symbol(sent_mint)
    sent_amount = first_transfer_dict['tokenAmount']
    if sent_symbol is None:
        sent_symbol = TOKEN_SYMBOLS.get(t["mint"], "UNKNOWN")
    

    # ---------- TRANSFER ----------
    if tx_type == "TRANSFER" and tx.get('fee') < 8000: # excluding SOL transfers which have 10000 lamports fee
        if "to multiple accounts" in tx['description']:
            logger.warning(f"Transaction {signature} is spam transfer to multiple accounts, skipping")
            return None

        if tx.get("tokenTransfers"):
            t = tx["tokenTransfers"][0]
            if t["tokenAmount"] > 0:
                return {
                    "signature": signature,
                    "wallet": wallet,
                    "side": "TRANSFER",
                    "sent_amount": sent_amount,
                    "sent_symbol": sent_symbol,
                    "to_address": t["toUserAccount"],
                    "description": tx.get("description")
                }

        if tx.get("nativeTransfers"):
            t = tx["nativeTransfers"][0]
            if t["amount"] > 100:
                return {
                    "signature": signature,
                    "wallet": wallet,
                    "side": "TRANSFER",
                    "sent_amount": sent_amount / 1_000_000_000,
                    "sent_symbol": "SOL",
                    "to_address": t["toUserAccount"],
                    "description": tx.get("description")
                }

        return None

    # ---------- SWAP (including Jupiter UNKNOWN) ----------
    if tx_type == "SWAP":
        balance_changes = defaultdict(float)

        # SPL token transfers
        for t in tx.get("tokenTransfers", []):
            mint = t["mint"]
            amount = float(t["tokenAmount"])

            if t.get("fromUserAccount") == wallet:
                balance_changes[mint] -= amount

            if t.get("toUserAccount") == wallet:
                balance_changes[mint] += amount
        if not balance_changes:
            logger.warning(f"No balance changes for tx {signature}")
            return None
        # -- SOL (native) delta for aggregator such as Wintermute Bot --
        if TOKEN_SYMBOLS["SOL"] not in balance_changes and len(balance_changes) < 2:
            balance_changes[TOKEN_SYMBOLS["SOL"]] = 0

            # SOL delta calculation
            sol_delta = 0.0
            for t in tx.get("nativeTransfers", []):
                if t.get("fromUserAccount") == wallet:
                    sol_delta -= t["amount"] / 1_000_000_000
                if t.get("toUserAccount") == wallet:
                    sol_delta += t["amount"] / 1_000_000_000

            if balance_changes and abs(sol_delta) > 1e-6:
                balance_changes[TOKEN_SYMBOLS["SOL"]] += sol_delta
        # This swap token to token and not recieve for signer
        if TOKEN_SYMBOLS["SOL"] in balance_changes and balance_changes[TOKEN_SYMBOLS["SOL"]] == 0:
            balance_changes.clear()

            mint = tx['tokenTransfers'][0]["mint"]
            amount = float(tx['tokenTransfers'][0]["tokenAmount"])
            balance_changes[mint] = -amount
            
            first_transfer_own = tx['tokenTransfers'][0]['fromUserAccount']
            if first_transfer_own == wallet:
                
                to_user_reciever = tx['tokenTransfers'][0]['toUserAccount']
                for t in tx['tokenTransfers'][1:]:
                    if t['toUserAccount'].lower() == to_user_reciever.lower():
                        mint = t["mint"]
                        amount = float(t["tokenAmount"])
                        balance_changes[mint] = amount
            else:
                from_user_reciever = tx['tokenTransfers'][0]['fromUserAccount']
                for t in tx['tokenTransfers'][1:]:
                    if from_user_reciever.lower() == t['fromUserAccount'].lower() and wallet.lower() == t['toUserAccount'].lower():
                        mint = t["mint"]
                        amount = float(t["tokenAmount"])
                        balance_changes[mint] = amount
        # Filter zero / dust
        balance_changes = {
            mint: amt for mint, amt in balance_changes.items()
            if abs(amt) > 1e-9
        }

        if not balance_changes:
            logger.warning(f"Dust-only balance changes for tx {signature}")
            return None

        # SENT = biggest negative
        sent_mint, sent_amount = min(balance_changes.items(), key=lambda x: x[1])
        sent_symbol = await get_token_symbol(sent_mint)

        # RECEIVED = biggest positive
        recv_mint, recv_amount = max(balance_changes.items(), key=lambda x: x[1])
        recv_symbol = await get_token_symbol(recv_mint)

        if sent_amount >= 0 or recv_amount <= 0:
            logger.warning(f"Could not determine swap direction for tx {signature}")
        else:
            return {
                "signature": signature,
                "wallet": wallet,
                "side": "SWAP",
                "sent_amount": abs(sent_amount),
                "sent_symbol": sent_symbol,
                "recv_amount": recv_amount,
                "recv_symbol": recv_symbol if recv_symbol else TOKEN_SYMBOLS.get(recv_mint, recv_mint[:6]),
                "aggregator": AGGREGATORS.get(source, source),
                "description": tx.get("description")
            }

    # ---------- OTHER ----------
    logger.info(f"Transaction {signature} type={tx_type} source={source} skipped")

    return {
            "signature": signature,
            "wallet": wallet,
            "side": "SKIPPED",
            "sent_amount": sent_amount,
            "sent_symbol": sent_symbol,
            "description": tx.get("description")
        }


async def get_token_symbol(address: str):
    limits = httpx.Limits(
        max_connections=8,
        max_keepalive_connections=2
    )

    timeout = httpx.Timeout(15.0)

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        http2=False
    ) as client:
        url = f"https://api-mainnet.helius-rpc.com/v0/token-metadata"

        resp = await client.post(
        url,
        params={"api-key": config.helius_api_key},
        json={"mintAccounts": [address]}
    )

        if resp.status_code != 200:
            logger.error(f"Helius returned {resp.status_code} for get metadata {address}")
            return None

        
        data = resp.json()
        if not data:
            logger.error(f"No data returned from Helius API for tx {signature}, skipping all them!")
            return None
        metadata = data[0]
        try:
            return metadata['onChainMetadata']['metadata']['data']['symbol']
        except:
            return None
        
