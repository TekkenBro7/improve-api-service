from datetime import date
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.core.enums import CurrencyEnum
from src.database.models.user import User, UserBalance
from src.database.repositories.base_repository import BaseRepository
from src.exceptions.user_exceptions import UserAlreadyExistsException


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

    async def get_users(
        self,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        user_status: Optional[str] = None,
    ) -> list[tuple[User, list[UserBalance]]]:
        """
        Retrieve users with their balances.

        Args:
            user_id (Optional[int]): Filter users by their ID. Defaults to None.
            email (Optional[str]): Filter users by their email. Defaults to None.
            user_status (Optional[str]): Filter users by their status. Defaults to None.

        Returns:
            list[tuple[User, list[UserBalance]]]: A list of tuples, each containing
            a User object and a list of the user's balances.
        """
        q = (
            select(User)
            .options(selectinload(User.user_balance))
            .order_by(User.created_at.desc())
        )

        if user_id is not None:
            q = q.where(User.id == user_id)
        if email is not None:
            q = q.where(User.email == email)
        if user_status is not None:
            q = q.where(User.status == user_status)

        user_rows = await self.session.execute(q)
        users = user_rows.scalars().all()

        result = [(user, list(user.user_balance)) for user in users]

        return result

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user_with_balances(self, email: str) -> User:
        try:
            async with self.session.begin():
                db_user = User(email=email, status="ACTIVE")
                self.session.add(db_user)
                await self.session.flush()

                balances = [
                    UserBalance(user_id=db_user.id, currency=str(currency), amount=0)
                    for currency in CurrencyEnum
                ]
                self.session.add_all(balances)

            return db_user
        except IntegrityError:
            raise UserAlreadyExistsException(
                status_code=409,
                detail=f"User with email=`{email}` already exists",
            )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_status(self, user_id: int, status: str) -> User:
        q = update(User).values(status=status).where(User.id == user_id).returning(User)

        result = await self.session.execute(q)
        await self.session.commit()
        return result.scalar_one()
