from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, UserStatusEnum
from src.database.repositories.user_repository import UserRepository
from src.exceptions.general_exceptions import BadRequestDataException
from src.exceptions.user_exceptions import (
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserNotExistsException,
)
from src.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    UserModel,
)


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_users(
        self,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        user_status: Optional[str] = None,
    ) -> list[ResponseUserModel]:
        users = await self.repo.get_users(user_id, email, user_status)

        result_models = []

        for user, balances in users:
            user_model = ResponseUserModel(
                id=user.id,
                email=user.email,
                status=UserStatusEnum(user.status),
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            balance_models = [
                ResponseUserBalanceModel(
                    currency=CurrencyEnum(balance.currency),
                    amount=float(str(balance.amount)),
                )
                for balance in balances
            ]

            user_model.balances = sorted(
                balance_models,
                key=lambda x: x.amount if x.amount is not None else 0.0,
                reverse=True,
            )

            result_models.append(user_model)

        return result_models

    async def create_user(self, user: RequestUserModel) -> UserModel:
        email = user.email.strip()
        if not email:
            raise BadRequestDataException(
                status_code=422,
                detail="Email can't consist entirely of spaces",
            )

        db_user = await self.repo.create_user_with_balances(email)

        return UserModel(
            id=db_user.id,
            email=db_user.email,
            status=UserStatusEnum(db_user.status),
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )

    async def update_user_status(
        self, user_id: int, user_update: RequestUserUpdateModel
    ) -> UserModel:
        if user_id < 0:
            raise BadRequestDataException(
                status_code=422, detail="Unprocessable data in request"
            )

        db_user = await self.repo.get_user_by_id(user_id)
        if not db_user:
            raise UserNotExistsException(
                status_code=404, detail=f"User with id=`{user_id}` does not exist"
            )

        if db_user.status == "BLOCKED" and user_update.status == "BLOCKED":
            raise UserAlreadyBlockedException(
                status_code=400, detail=f"User with id=`{user_id}` is already blocked"
            )

        if db_user.status == "ACTIVE" and user_update.status == "ACTIVE":
            raise UserAlreadyActiveException(
                status_code=400, detail=f"User with id=`{user_id}` is already active"
            )

        updated_user = await self.repo.update_status(user_id, user_update.status)

        return UserModel(
            id=updated_user.id,
            email=updated_user.email,
            status=UserStatusEnum(updated_user.status),
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
        )
