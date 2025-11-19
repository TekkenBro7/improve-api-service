from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, insert, select, update

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
            (func.date(Transaction.created_at) >= dt_from)
            & (func.date(Transaction.created_at) <= dt_to)
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
            (func.date(Transaction.created_at) >= dt_from)
            & (func.date(Transaction.created_at) <= dt_to)
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
            (func.date(Transaction.created_at) >= dt_from)
            & (func.date(Transaction.created_at) <= dt_to)
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

    async def get_transactions(self, user_id: Optional[int]) -> list[Transaction]:
        query = select(Transaction).order_by(Transaction.created_at.desc())

        if user_id is not None:
            query = query.where(Transaction.user_id == user_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_transaction(
        self,
        user_id: int,
        currency: str,
        amount: float,
        status: str,
    ) -> Transaction:
        db_transaction = (
            insert(Transaction)
            .values(
                user_id=user_id,
                currency=currency,
                amount=amount,
                status=status,
            )
            .returning(Transaction)
        )

        result = await self.session.execute(db_transaction)
        await self.session.commit()

        return result.scalar_one()

    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def update_transaction_status(
        self,
        transaction_id: int,
        new_status: str,
    ) -> Transaction:
        q = (
            update(Transaction)
            .values(status=new_status)
            .where(Transaction.id == transaction_id)
            .returning(Transaction)
        )

        result = await self.session.execute(q)
        await self.session.commit()
        return result.scalar_one()
