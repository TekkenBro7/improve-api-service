from datetime import date

from sqlalchemy import func, select

from src.database.models.user import User
from src.database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    async def count_registered_between(self, dt_from: date, dt_to: date) -> int:
        """
        Count the number of users registered within a specified date range.

        Args:
            dt_from (date): Start date of the range.
            dt_to (date): End date of the range.

        Returns:
            int: Total number of users registered between dt_from and dt_to.
        """
        q = select(func.count(User.id)).where(
            (func.date(User.created_at) >= dt_from)
            & (func.date(User.created_at) <= dt_to)
        )
        result = await self.session.execute(q)
        return result.scalar_one()

    async def get_registered_between(self, dt_from: date, dt_to: date) -> list[User]:
        """
        Retrieve all users registered within a specified date range.

        Args:
            dt_from (date): Start date of the range.
            dt_to (date): End date of the range.

        Returns:
            list[User]: List of User objects registered between dt_from and dt_to.
        """
        q = select(User).where(
            (func.date(User.created_at) >= dt_from)
            & (func.date(User.created_at) <= dt_to)
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())
