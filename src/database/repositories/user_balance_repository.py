from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update

from src.database.models.user import UserBalance
from src.database.repositories.base_repository import BaseRepository


class UserBalanceRepository(BaseRepository):
    async def get_user_balance(
        self, user_id: int, currency: str
    ) -> Optional[UserBalance]:
        q = select(UserBalance).where(
            (UserBalance.user_id == user_id) & (UserBalance.currency == currency)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def update_balance(self, balance_id: int, new_amount: Decimal) -> None:
        q = (
            update(UserBalance)
            .values(amount=new_amount)
            .where(UserBalance.id == balance_id)
        )
        await self.session.execute(q)
        await self.session.commit()
