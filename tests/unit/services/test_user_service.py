import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserStatusEnum
from src.exceptions.general_exceptions import BadRequestDataException
from src.exceptions.user_exceptions import (
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserNotExistsException,
)
from src.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    UserModel,
)
from src.services.user_service import UserService


class TestUserService:
    @pytest_asyncio.fixture
    async def user_service(self, db_session: AsyncSession) -> UserService:
        return UserService(db_session)

    @pytest_asyncio.fixture
    async def sample_user_data(self, user_service: UserService) -> UserModel:
        user_data = RequestUserModel(email="test@example.com")
        user = await user_service.create_user(user_data)
        return user

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service: UserService) -> None:
        user_data = RequestUserModel(email="newuser@example.com")

        user = await user_service.create_user(user_data)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_user_empty_email(self, user_service: UserService) -> None:
        user_data = RequestUserModel(email=" ")

        with pytest.raises(BadRequestDataException):
            await user_service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_get_users_all(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        users = await user_service.get_users()

        assert len(users) >= 1
        assert any(user.id == sample_user_data.id for user in users)

    @pytest.mark.asyncio
    async def test_get_users_by_id(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        users = await user_service.get_users(user_id=sample_user_data.id)

        assert len(users) == 1
        assert users[0].id == sample_user_data.id
        assert users[0].balances is not None
        assert len(users[0].balances) > 0

    @pytest.mark.asyncio
    async def test_get_users_by_email(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        users = await user_service.get_users(email=sample_user_data.email)

        assert len(users) == 1
        assert users[0].email == sample_user_data.email

    @pytest.mark.asyncio
    async def test_update_user_status_to_blocked(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)

        assert sample_user_data.id is not None
        updated_user = await user_service.update_user_status(
            sample_user_data.id, update_data
        )

        assert updated_user.id == sample_user_data.id
        assert updated_user.status == "BLOCKED"

    @pytest.mark.asyncio
    async def test_update_user_status_to_active(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)
        assert sample_user_data.id is not None
        await user_service.update_user_status(sample_user_data.id, update_data)

        update_data = RequestUserUpdateModel(status=UserStatusEnum.ACTIVE)
        assert sample_user_data.id is not None
        updated_user = await user_service.update_user_status(
            sample_user_data.id, update_data
        )

        assert updated_user.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_update_user_status_already_blocked(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)
        assert sample_user_data.id is not None
        await user_service.update_user_status(sample_user_data.id, update_data)

        with pytest.raises(UserAlreadyBlockedException):
            assert sample_user_data.id is not None
            await user_service.update_user_status(sample_user_data.id, update_data)

    @pytest.mark.asyncio
    async def test_update_user_status_already_active(
        self, user_service: UserService, sample_user_data: UserModel
    ) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.ACTIVE)

        with pytest.raises(UserAlreadyActiveException):
            assert sample_user_data.id is not None
            await user_service.update_user_status(sample_user_data.id, update_data)

    @pytest.mark.asyncio
    async def test_update_user_status_not_found(self, user_service: UserService) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)

        with pytest.raises(UserNotExistsException):
            await user_service.update_user_status(99999, update_data)

    @pytest.mark.asyncio
    async def test_update_user_status_invalid_id(self, user_service: UserService) -> None:
        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)

        with pytest.raises(BadRequestDataException):
            await user_service.update_user_status(-1, update_data)
