from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import config

engine = create_async_engine(
    config.database_path,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSession = async_sessionmaker(engine, expire_on_commit=False)
