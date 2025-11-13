from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    user_balance: Mapped[list["UserBalance"]] = relationship(
        "UserBalance", back_populates="owner"
    )


class UserBalance(Base):
    __tablename__ = "user_balance"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="user_balance_user_currency_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[Numeric] = mapped_column(Numeric, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="user_balance")


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[Numeric] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
