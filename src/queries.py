from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db_models import Transaction, User
from src.python_models import CurrencyEnum

EXCHANGE_RATES_TO_USD = {
    CurrencyEnum.USD: 1,
    CurrencyEnum.EUR: 0.9342,
    CurrencyEnum.AUD: 0.5447,
    CurrencyEnum.CAD: 0.6162,
    CurrencyEnum.ARS: 0.0009,
    CurrencyEnum.PLN: 0.2343,
    CurrencyEnum.BTC: 100000.0,
    CurrencyEnum.ETH: 3557.3476,
    CurrencyEnum.DOGE: 0.3627,
    CurrencyEnum.USDT: 0.9709,
}


async def get_registered_users_count(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> int:
    q = select(User).where(
        (func.date(User.created >= dt_gt)) & (func.date(User.created) <= dt_lt)
    )
    count = await session.execute(q)
    registered_users = count.scalars().all()
    return len(registered_users)


async def get_registered_and_deposit_users_count(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> int:
    count = 0
    user_query = select(User).where(
        (func.date(User.created) >= dt_gt) & (func.date(User.created) <= dt_lt)
    )
    users_result = await session.execute(user_query)
    registered_users = users_result.scalars().all()
    for user in registered_users:
        transaction_query = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
        )
        deposits_result = await session.execute(transaction_query)
        deposits = deposits_result.scalars().all()
        if len(deposits) > 0:
            count += 1
    return count


async def get_registered_and_not_rollbacked_deposit_users_count(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> int:
    count = 0
    user_query = select(User).where(
        (func.date(User.created >= dt_gt)) & (func.date(User.created) <= dt_lt)
    )
    users_result = await session.execute(user_query)
    registered_users = users_result.scalars().all()
    for user in registered_users:
        transaction_query = select(Transaction).where(
            (func.date(Transaction.created) >= dt_gt)
            & (func.date(Transaction.created) <= dt_lt)
            & (Transaction.user_id == user.id)
            & (Transaction.amount > 0)
            & (Transaction.status != "ROLLBACKED")
        )
        deposits_result = await session.execute(transaction_query)
        not_rollbacked_deposits = deposits_result.scalars().all()
        if len(not_rollbacked_deposits) > 0:
            count += 1
    return count


async def get_not_rollbacked_deposit_amount(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> Decimal:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount > 0)
        & (Transaction.status != "ROLLBACKED")
    )
    result = await session.execute(q)
    not_rollbacked_deposits = result.scalars().all()

    total_amount = Decimal("0.0")
    for transaction in not_rollbacked_deposits:
        currency_enum = CurrencyEnum(transaction.currency)
        rate = Decimal(str(EXCHANGE_RATES_TO_USD[currency_enum]))
        amount = Decimal(str(transaction.amount))
        total_amount += amount * rate

    return total_amount


async def get_not_rollbacked_withdraw_amount(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> Decimal:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.amount < 0)
        & (Transaction.status != "ROLLBACKED")
    )
    result = await session.execute(q)
    not_rollbacked_withdraws = result.scalars().all()

    total_amount = Decimal("0.0")
    for transaction in not_rollbacked_withdraws:
        currency_enum = CurrencyEnum(transaction.currency)
        rate = Decimal(str(EXCHANGE_RATES_TO_USD[currency_enum]))
        transaction_amount = Decimal(str(transaction.amount))
        total_amount += transaction_amount * rate

    return total_amount


async def get_transactions_count(session: AsyncSession, dt_gt: date, dt_lt: date) -> int:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
    )
    result = await session.execute(q)
    transactions = result.fetchall()
    return len(transactions)


async def get_not_rollbacked_transactions_count(
    session: AsyncSession, dt_gt: date, dt_lt: date
) -> int:
    q = select(Transaction).where(
        (func.date(Transaction.created) >= dt_gt)
        & (func.date(Transaction.created) <= dt_lt)
        & (Transaction.status != "ROLLBACKED")
    )
    result = await session.execute(q)
    transactions = result.fetchall()
    return len(transactions)
