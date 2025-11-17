from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from src.core.enums import CurrencyEnum
from src.database.models.transaction import Transaction
from src.database.repositories.base_repository import BaseRepository

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


class TransactionRepository(BaseRepository):
    async def count_transactions_between(
        self, dt_from: date, dt_to: date, exclude_rollbacked: bool = False
    ) -> int:
        """
        Count the number of transactions within the given date range.

        Args:
            dt_from (date): Start date of the range.
            dt_to (date): End date of the range.
            exclude_rollbacked (bool): If True, exclude transactions with status 'ROLLBACKED'.

        Returns:
            int: Total number of transactions matching the criteria.
        """
        q = select(func.count(Transaction.id)).where(
            (func.date(Transaction.created) >= dt_from)
            & (func.date(Transaction.created) <= dt_to)
        )
        if exclude_rollbacked:
            q = q.where(Transaction.status != "ROLLBACKED")

        result = await self.session.execute(q)
        return result.scalar_one()

    async def get_transactions_between(
        self, dt_from: date, dt_to: date, exclude_rollbacked: bool = False
    ) -> list[Transaction]:
        """
        Retrieve all transactions within the specified date range.

        Args:
            dt_from (date): Start date of the range.
            dt_to (date): End date of the range.
            exclude_rollbacked (bool): If True, exclude transactions with status 'ROLLBACKED'.

        Returns:
            list[Transaction]: List of Transaction objects matching the criteria.
        """
        q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_from)
            & (func.date(Transaction.created) <= dt_to)
        )
        if exclude_rollbacked:
            q = q.where(Transaction.status != "ROLLBACKED")

        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_total_amount_between(
        self,
        dt_from: date,
        dt_to: date,
        deposits_only: bool = False,
        withdraws_only: bool = False,
        exclude_rollbacked: bool = False,
    ) -> Decimal:
        """
        Calculate the total amount of transactions in USD within a date range.

        Args:
            dt_from (date): Start date of the range.
            dt_to (date): End date of the range.
            deposits_only (bool): If True, only include deposits (amount > 0).
            withdraws_only (bool): If True, only include withdrawals (amount < 0).
            exclude_rollbacked (bool): If True, exclude transactions with status 'ROLLBACKED'.

        Returns:
            Decimal: Total transaction amount converted to USD.
        """
        q = select(Transaction).where(
            (func.date(Transaction.created) >= dt_from)
            & (func.date(Transaction.created) <= dt_to)
        )

        if deposits_only:
            q = q.where(Transaction.amount > 0)
        elif withdraws_only:
            q = q.where(Transaction.amount < 0)

        if exclude_rollbacked:
            q = q.where(Transaction.status != "ROLLBACKED")

        result = await self.session.execute(q)
        transactions = result.scalars().all()

        total_amount = Decimal("0.0")
        for transaction in transactions:
            currency_enum = CurrencyEnum(transaction.currency)
            rate = Decimal(str(EXCHANGE_RATES_TO_USD[currency_enum]))
            amount = Decimal(str(transaction.amount))
            total_amount += amount * rate

        return total_amount
