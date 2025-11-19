from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum
from src.schemas.transaction import RequestTransactionModel
from src.schemas.user import RequestUserModel, UserModel
from src.services.analytics_service import AnalyticsService
from src.services.transactions_service import TransactionsService
from src.services.user_service import UserService


class TestAnalyticsService:
    @pytest_asyncio.fixture
    async def analytics_service(self, db_session: AsyncSession) -> AnalyticsService:
        return AnalyticsService(db_session)

    @pytest_asyncio.fixture
    async def user_service(self, db_session: AsyncSession) -> UserService:
        return UserService(db_session)

    @pytest_asyncio.fixture
    async def transactions_service(self, db_session: AsyncSession) -> TransactionsService:
        return TransactionsService(db_session)

    @pytest_asyncio.fixture
    async def sample_user_with_transactions(
        self, user_service: UserService, transactions_service: TransactionsService
    ) -> UserModel:
        user_data = RequestUserModel(email="analytics_user@example.com")
        user = await user_service.create_user(user_data)

        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=200.0)
        withdrawal_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=-50.0)

        assert user.id is not None
        await transactions_service.create_transaction(user.id, deposit_data)
        await transactions_service.create_transaction(user.id, withdrawal_data)

        return user

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_returns_correct_structure(
        self,
        analytics_service: AnalyticsService,
        sample_user_with_transactions: UserModel,
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        assert isinstance(results, list)
        assert len(results) > 0

        first_week = results[0]
        expected_keys = {
            "start_date",
            "end_date",
            "registered_users_count",
            "deposit_distinct_users_count",
            "not_rollbacked_deposit_amount",
            "not_rollbacked_withdraw_amount",
            "transactions_count",
            "not_rollbacked_transactions_count",
        }

        assert set(first_week.keys()) == expected_keys
        assert isinstance(first_week["start_date"], date)
        assert isinstance(first_week["end_date"], date)
        assert isinstance(first_week["registered_users_count"], int)
        assert isinstance(first_week["deposit_distinct_users_count"], int)
        assert isinstance(first_week["not_rollbacked_deposit_amount"], Decimal)
        assert isinstance(first_week["not_rollbacked_withdraw_amount"], Decimal)
        assert isinstance(first_week["transactions_count"], int)
        assert isinstance(first_week["not_rollbacked_transactions_count"], int)

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_weeks_ordering(
        self, analytics_service: AnalyticsService
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        assert len(results) > 1

        for i in range(len(results) - 1):
            current_week = results[i]
            next_week = results[i + 1]

            assert current_week["start_date"] > next_week["start_date"]
            assert current_week["end_date"] > next_week["end_date"]

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_with_transactions_data(
        self,
        analytics_service: AnalyticsService,
        sample_user_with_transactions: UserModel,
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        current_week = results[0]

        assert current_week["registered_users_count"] == 1
        assert current_week["deposit_distinct_users_count"] == 1
        assert current_week["transactions_count"] == 2
        assert current_week["not_rollbacked_transactions_count"] == 2

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_amounts_calculation(
        self,
        analytics_service: AnalyticsService,
        sample_user_with_transactions: UserModel,
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        current_week = results[0]

        assert current_week["not_rollbacked_deposit_amount"] > Decimal("0")
        assert current_week["not_rollbacked_withdraw_amount"] < Decimal("0")

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_multiple_users(
        self,
        analytics_service: AnalyticsService,
        user_service: UserService,
        transactions_service: TransactionsService,
    ) -> None:
        user1_data = RequestUserModel(email="user1_analytics@example.com")
        user1 = await user_service.create_user(user1_data)

        user2_data = RequestUserModel(email="user2_analytics@example.com")
        user2 = await user_service.create_user(user2_data)

        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)

        assert user1.id is not None
        assert user2.id is not None
        await transactions_service.create_transaction(user1.id, deposit_data)
        await transactions_service.create_transaction(user2.id, deposit_data)

        results = await analytics_service.get_weekly_analysis()
        current_week = results[0]

        assert current_week["registered_users_count"] == 2
        assert current_week["deposit_distinct_users_count"] == 2
        assert current_week["transactions_count"] == 2

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_different_currencies(
        self,
        analytics_service: AnalyticsService,
        user_service: UserService,
        transactions_service: TransactionsService,
    ) -> None:
        user_data = RequestUserModel(email="multi_currency_user@example.com")
        user = await user_service.create_user(user_data)

        usd_deposit = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)
        eur_deposit = RequestTransactionModel(currency=CurrencyEnum.EUR, amount=50.0)

        assert user.id is not None
        await transactions_service.create_transaction(user.id, usd_deposit)
        await transactions_service.create_transaction(user.id, eur_deposit)

        results = await analytics_service.get_weekly_analysis()
        current_week = results[0]

        assert current_week["transactions_count"] >= 2
        assert current_week["not_rollbacked_deposit_amount"] > Decimal("0")

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_rollbacked_transactions_excluded(
        self,
        analytics_service: AnalyticsService,
        user_service: UserService,
        transactions_service: TransactionsService,
    ) -> None:
        user_data = RequestUserModel(email="rollback_test_user@example.com")
        user = await user_service.create_user(user_data)

        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)

        assert user.id is not None
        transaction = await transactions_service.create_transaction(user.id, deposit_data)

        assert transaction.id is not None
        await transactions_service.rollback_transaction(user.id, transaction.id)

        results = await analytics_service.get_weekly_analysis()
        current_week = results[0]

        assert current_week["transactions_count"] >= 1
        assert current_week["not_rollbacked_transactions_count"] == 0
        assert current_week["not_rollbacked_deposit_amount"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_week_boundaries_correct(
        self, analytics_service: AnalyticsService
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        for week in results:
            start_date = week["start_date"]
            end_date = week["end_date"]

            assert start_date.weekday() == 0
            assert end_date.weekday() == 6
            assert (end_date - start_date).days == 6

    @pytest.mark.asyncio
    async def test_get_weekly_analysis_consistent_week_duration(
        self, analytics_service: AnalyticsService
    ) -> None:
        results = await analytics_service.get_weekly_analysis()

        for i in range(len(results) - 1):
            current_week = results[i]
            next_week = results[i + 1]

            current_duration = (
                current_week["end_date"] - current_week["start_date"]
            ).days
            next_duration = (next_week["end_date"] - next_week["start_date"]).days

            assert current_duration == 6
            assert next_duration == 6
            assert (current_week["start_date"] - next_week["start_date"]).days == 7
