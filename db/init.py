# db/init.py
from pathlib import Path
from db.engine import engine
from db.models import Base

async def init_db():
    Path("./data").mkdir(exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
