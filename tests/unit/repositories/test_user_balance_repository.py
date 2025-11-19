from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum
from src.database.models.user import User, UserBalance
from src.database.repositories.user_balance_repository import UserBalanceRepository
from src.database.repositories.user_repository import UserRepository


class TestUserBalanceRepository:
    @pytest_asyncio.fixture
    async def balance_repo(self, db_session: AsyncSession) -> UserBalanceRepository:
        return UserBalanceRepository(db_session)

    @pytest_asyncio.fixture
    async def user_repo(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    @pytest_asyncio.fixture
    async def sample_user(self, user_repo: UserRepository) -> User:
        user = await user_repo.create_user_with_balances("test@example.com")
        return user

    @pytest_asyncio.fixture
    async def sample_balance(
        self, balance_repo: UserBalanceRepository, sample_user: User
    ) -> UserBalance:
        balance = await balance_repo.get_user_balance(sample_user.id, "USD")
        assert balance is not None
        return balance

    @pytest.mark.asyncio
    async def test_get_user_balance_found(
        self, balance_repo: UserBalanceRepository, sample_balance: UserBalance
    ) -> None:
        found_balance = await balance_repo.get_user_balance(
            sample_balance.user_id, sample_balance.currency
        )

        assert found_balance is not None
        assert found_balance.id == sample_balance.id
        assert found_balance.user_id == sample_balance.user_id
        assert found_balance.currency == sample_balance.currency
        assert found_balance.amount == 0

    @pytest.mark.asyncio
    async def test_get_user_balance_not_found(
        self, balance_repo: UserBalanceRepository
    ) -> None:
        found_balance = await balance_repo.get_user_balance(99999, "USD")

        assert found_balance is None

    @pytest.mark.asyncio
    async def test_get_user_balance_wrong_currency(
        self, balance_repo: UserBalanceRepository, sample_user: User
    ) -> None:
        found_balance = await balance_repo.get_user_balance(sample_user.id, "WRONG")

        assert found_balance is None

    @pytest.mark.asyncio
    async def test_update_balance_success(
        self, balance_repo: UserBalanceRepository, sample_balance: UserBalance
    ) -> None:
        new_amount = Decimal("150.75")

        await balance_repo.update_balance(sample_balance.id, new_amount)

        updated_balance = await balance_repo.get_user_balance(
            sample_balance.user_id, sample_balance.currency
        )

        assert updated_balance is not None
        assert updated_balance.amount == new_amount

    @pytest.mark.asyncio
    async def test_get_all_balances_for_user(
        self, balance_repo: UserBalanceRepository, sample_user: User
    ) -> None:
        for currency in CurrencyEnum:
            balance = await balance_repo.get_user_balance(sample_user.id, str(currency))
            assert balance is not None
            assert balance.user_id == sample_user.id
            assert balance.currency == str(currency)
            assert balance.amount == 0
