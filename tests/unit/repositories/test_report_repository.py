from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.repositories.report_repository import ReportRepository
from src.database.repositories.transaction_repository import TransactionRepository
from src.database.repositories.user_repository import UserRepository


class TestReportRepository:
    @pytest_asyncio.fixture
    async def report_repo(self, db_session: AsyncSession) -> ReportRepository:
        return ReportRepository(db_session)

    @pytest_asyncio.fixture
    async def transaction_repo(self, db_session: AsyncSession) -> TransactionRepository:
        return TransactionRepository(db_session)

    @pytest_asyncio.fixture
    async def user_repo(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    @pytest_asyncio.fixture
    async def user_with_deposit(
        self, user_repo: UserRepository, transaction_repo: TransactionRepository
    ) -> User:
        user = await user_repo.create_user_with_balances("deposit_user@example.com")
        await transaction_repo.create_transaction(
            user_id=user.id, currency="USD", amount=100.0, status="PROCESSED"
        )
        return user

    @pytest_asyncio.fixture
    async def user_without_deposit(
        self, user_repo: UserRepository, transaction_repo: TransactionRepository
    ) -> User:
        user = await user_repo.create_user_with_balances("no_deposit_user@example.com")
        await transaction_repo.create_transaction(
            user_id=user.id, currency="USD", amount=-50.0, status="PROCESSED"
        )
        return user

    @pytest.mark.asyncio
    async def test_count_users_with_deposit_between_success(
        self, report_repo: ReportRepository, user_with_deposit: User
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count = await report_repo.count_users_with_deposit_between(start_date, end_date)

        assert count >= 1

    @pytest.mark.asyncio
    async def test_count_users_with_deposit_between_no_users(
        self, report_repo: ReportRepository
    ) -> None:
        future_date = date.today() + timedelta(days=365)

        count = await report_repo.count_users_with_deposit_between(
            future_date, future_date
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_users_with_deposit_between_excludes_withdrawals(
        self, report_repo: ReportRepository, user_without_deposit: User
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count = await report_repo.count_users_with_deposit_between(start_date, end_date)

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_users_with_deposit_between_multiple_users(
        self,
        report_repo: ReportRepository,
        user_with_deposit: User,
        user_repo: UserRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        another_user = await user_repo.create_user_with_balances(
            "another_deposit_user@example.com"
        )
        await transaction_repo.create_transaction(
            user_id=another_user.id, currency="EUR", amount=200.0, status="PROCESSED"
        )

        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count = await report_repo.count_users_with_deposit_between(start_date, end_date)

        assert count >= 2
