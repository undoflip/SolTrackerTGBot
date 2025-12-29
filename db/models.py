from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Boolean, ForeignKey, String

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    address: Mapped[str] = mapped_column(String, index=True)
    label: Mapped[str]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mint: Mapped[str] = mapped_column(unique=True)
    symbol: Mapped[str]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
