import asyncio
import random
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from src.core.logger import logger
from src.database.models.transaction import Transaction
from src.database.models.user import User, UserBalance
from src.database.session import get_async_session


async def clear_db(session: AsyncSession) -> None:
    logger.info("Clearing database...")
    try:
        await session.execute(
            text('TRUNCATE TABLE "transaction", "user_balance", "user" CASCADE')
        )
        await session.commit()
        logger.info("Database cleared successfully!")
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to clear database: {e}")
        raise


async def seed_db() -> None:
    logger.info("Seeding database started")

    async for session in get_async_session():
        await clear_db(session)

        users = []
        for i in range(10):
            user = User(
                email=f"user{i}@example.com",
                status=random.choice(list(UserStatusEnum)).value,
            )
            session.add(user)
            users.append(user)

        await session.flush()

        for user in users:
            for currency in CurrencyEnum:
                balance = UserBalance(
                    user_id=user.id,
                    currency=currency.value,
                    amount=Decimal(random.randint(0, 1000)),
                )
                session.add(balance)

        for user in users:
            for _ in range(5):
                transaction = Transaction(
                    user_id=user.id,
                    currency=random.choice(list(CurrencyEnum)).value,
                    amount=Decimal(random.randint(-500, 500)),
                    status=random.choice(list(TransactionStatusEnum)).value,
                )
                session.add(transaction)

        await session.commit()

    logger.info("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_db())
