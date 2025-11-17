from datetime import date

from sqlalchemy import distinct, func, select

from src.database.models.transaction import Transaction
from src.database.models.user import User
from src.database.repositories.base_repository import BaseRepository


class ReportRepository(BaseRepository):
    async def count_users_with_deposit_between(self, dt_from: date, dt_to: date) -> int:
        """
        Count the number of unique users who made at least one deposit
        within the specified date range.

        Args:
            dt_from (date): Start date of the period.
            dt_to (date): End date of the period.

        Returns:
            int: Number of unique users with deposits.
        """
        q = (
            select(func.count(distinct(User.id)))
            .join(Transaction, Transaction.user_id == User.id)
            .where(
                (func.date(User.created_at) >= dt_from)
                & (func.date(User.created_at) <= dt_to)
                & (func.date(Transaction.created_at) >= dt_from)
                & (func.date(Transaction.created_at) <= dt_to)
                & (Transaction.amount > 0)
            )
        )
        result = await self.session.execute(q)
        return result.scalar_one()

    async def count_users_with_non_rollbacked_deposits(
        self, dt_from: date, dt_to: date
    ) -> int:
        """
        Count the number of unique users who made at least one non-rollbacked deposit
        within the specified date range.

        Args:
            dt_from (date): Start date of the period.
            dt_to (date): End date of the period.

        Returns:
            int: Number of unique users with non-rollbacked deposits.
        """
        q = (
            select(func.count(distinct(User.id)))
            .join(Transaction, Transaction.user_id == User.id)
            .where(
                (func.date(User.created_at) >= dt_from)
                & (func.date(User.created_at) <= dt_to)
                & (func.date(Transaction.created_at) >= dt_from)
                & (func.date(Transaction.created_at) <= dt_to)
                & (Transaction.amount > 0)
                & (Transaction.status != "ROLLBACKED")
            )
        )
        result = await self.session.execute(q)
        return result.scalar_one()
