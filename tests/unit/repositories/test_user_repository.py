from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum
from src.database.models.user import User, UserBalance
from src.database.repositories.user_repository import UserRepository
from src.exceptions.user_exceptions import UserAlreadyExistsException


class TestUserRepository:
    @pytest_asyncio.fixture
    async def user_repo(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    @pytest_asyncio.fixture
    async def sample_user(self, user_repo: UserRepository) -> User:
        user = await user_repo.create_user_with_balances("test@example.com")
        return user

    @pytest_asyncio.fixture
    async def multiple_users(self, user_repo: UserRepository) -> list[User]:
        users = []
        for i in range(3):
            user = await user_repo.create_user_with_balances(f"user{i}@example.com")
            users.append(user)
        return users

    @pytest.mark.asyncio
    async def test_create_user_with_balances_success(
        self, user_repo: UserRepository
    ) -> None:
        user = await user_repo.create_user_with_balances("newuser@example.com")

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.status == "ACTIVE"

        balances = await user_repo.session.execute(
            select(UserBalance).where(UserBalance.user_id == user.id)
        )
        balance_records = balances.scalars().all()

        assert len(balance_records) == len(CurrencyEnum)
        for currency in CurrencyEnum:
            assert any(balance.currency == str(currency) for balance in balance_records)

    @pytest.mark.asyncio
    async def test_create_user_with_balances_duplicate_email(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        with pytest.raises(UserAlreadyExistsException):
            await user_repo.create_user_with_balances("test@example.com")

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        found_user = await user_repo.get_user_by_email("test@example.com")

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_repo: UserRepository) -> None:
        found_user = await user_repo.get_user_by_email("nonexistent@example.com")

        assert found_user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        found_user = await user_repo.get_user_by_id(sample_user.id)

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_repo: UserRepository) -> None:
        found_user = await user_repo.get_user_by_id(99999)

        assert found_user is None

    @pytest.mark.asyncio
    async def test_get_users_with_balances_all(
        self, user_repo: UserRepository, multiple_users: list[User]
    ) -> None:
        users_with_balances = await user_repo.get_users()

        assert len(users_with_balances) >= 3

        for user, balances in users_with_balances:
            assert isinstance(user, User)
            assert isinstance(balances, list)
            assert all(isinstance(balance, UserBalance) for balance in balances)
            assert len(balances) == len(CurrencyEnum)

    @pytest.mark.asyncio
    async def test_get_users_with_balances_by_id(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(user_id=sample_user.id)

        assert len(users_with_balances) == 1

        user, balances = users_with_balances[0]
        assert user.id == sample_user.id
        assert len(balances) == len(CurrencyEnum)

    @pytest.mark.asyncio
    async def test_get_users_with_balances_by_email(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(email=sample_user.email)

        assert len(users_with_balances) == 1

        user, balances = users_with_balances[0]
        assert user.email == sample_user.email
        assert len(balances) == len(CurrencyEnum)

    @pytest.mark.asyncio
    async def test_get_users_with_balances_by_status(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(user_status="ACTIVE")

        assert len(users_with_balances) >= 1
        assert all(user.status == "ACTIVE" for user, _ in users_with_balances)

    @pytest.mark.asyncio
    async def test_count_registered_between(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count = await user_repo.count_registered_between(start_date, end_date)

        assert count >= 1

    @pytest.mark.asyncio
    async def test_count_registered_between_no_users(
        self, user_repo: UserRepository
    ) -> None:
        future_date = date.today() + timedelta(days=365)

        count = await user_repo.count_registered_between(future_date, future_date)

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_registered_between(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        users = await user_repo.get_registered_between(start_date, end_date)

        assert len(users) >= 1
        assert any(user.id == sample_user.id for user in users)

    @pytest.mark.asyncio
    async def test_get_registered_between_no_users(
        self, user_repo: UserRepository
    ) -> None:
        future_date = date.today() + timedelta(days=365)

        users = await user_repo.get_registered_between(future_date, future_date)

        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_update_status_success(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        updated_user = await user_repo.update_status(sample_user.id, "BLOCKED")

        assert updated_user.id == sample_user.id
        assert updated_user.status == "BLOCKED"

        db_user = await user_repo.get_user_by_id(sample_user.id)
        assert db_user is not None
        assert db_user.status == "BLOCKED"

    @pytest.mark.asyncio
    async def test_user_balance_initial_values(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(user_id=sample_user.id)

        _, balances = users_with_balances[0]

        for balance in balances:
            assert balance.amount == 0
            assert balance.currency in [str(currency) for currency in CurrencyEnum]
            assert balance.user_id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_users_ordering(
        self, user_repo: UserRepository, multiple_users: list[User]
    ) -> None:
        users_with_balances = await user_repo.get_users()

        created_dates = [user.created_at for user, _ in users_with_balances]
        assert created_dates == sorted(created_dates, reverse=True)

    @pytest.mark.asyncio
    async def test_get_users_empty(self, user_repo: UserRepository) -> None:
        users_with_balances = await user_repo.get_users()

        assert len(users_with_balances) == 0

    @pytest.mark.asyncio
    async def test_get_users_with_filters_combined(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(
            user_id=sample_user.id, email=sample_user.email
        )

        assert len(users_with_balances) == 1
        user, balances = users_with_balances[0]
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    @pytest.mark.asyncio
    async def test_get_users_with_non_matching_filters(
        self, user_repo: UserRepository, sample_user: User
    ) -> None:
        users_with_balances = await user_repo.get_users(
            user_id=sample_user.id, email="wrong@example.com"
        )

        assert len(users_with_balances) == 0
