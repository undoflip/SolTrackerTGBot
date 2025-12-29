import asyncio
from sqlalchemy import select
from db.engine import AsyncSession
from db.models import Wallet, User
from solana_tracker import listen_wallet

class WalletDispatcher:
    def __init__(self, queue):
        self.queue = queue
        self.tasks: dict[str, asyncio.Task] = {}

    async def load_enabled_wallets(self) -> set[str]:
        async with AsyncSession() as session:
            result = await session.execute(
                select(Wallet.address)
                .join(User)
                .where(
                    Wallet.enabled.is_(True),
                    User.enabled.is_(True)
                )
            )
            return set(result.scalars().all())

    async def run(self):
        while True:
            enabled_wallets = await self.load_enabled_wallets()

            # ➕ запускаем новые
            for address in enabled_wallets:
                if address not in self.tasks:
                    self.tasks[address] = asyncio.create_task(
                        listen_wallet(address, self.queue)
                    )

            # ➖ останавливаем выключенные
            for address in list(self.tasks):
                if address not in enabled_wallets:
                    self.tasks[address].cancel()
                    del self.tasks[address]

            await asyncio.sleep(5)
