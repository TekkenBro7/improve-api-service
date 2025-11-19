from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestAnalyticsAPI:
    @pytest_asyncio.fixture
    async def test_users(self, client: AsyncClient) -> list[dict]:
        users = []
        for i in range(5):
            response = await client.post(
                "/api/v1/users", json={"email": f"analytics_test_user_{i}@example.com"}
            )
            users.append(response.json())
        return users

    @pytest_asyncio.fixture
    async def test_transactions(
        self, client: AsyncClient, test_users: list[dict]
    ) -> list[dict]:
        transactions = []

        for i, user in enumerate(test_users[:3]):
            response = await client.post(
                f"/api/v1/transactions/{user['id']}",
                json={"currency": "USD", "amount": 100.0 * (i + 1)},
            )
            transactions.append(response.json())

        for i, user in enumerate(test_users[:2]):
            response = await client.post(
                f"/api/v1/transactions/{user['id']}",
                json={"currency": "USD", "amount": -50.0 * (i + 1)},
            )
            transactions.append(response.json())

        rollback_response = await client.patch(
            f"/api/v1/transactions/{transactions[0]['id']}/users/{test_users[0]['id']}"
        )
        transactions[0] = rollback_response.json()

        return transactions

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_success(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        first_week = data[0]
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

        assert isinstance(first_week["start_date"], str)
        assert isinstance(first_week["end_date"], str)

        assert isinstance(first_week["registered_users_count"], int)
        assert isinstance(first_week["deposit_distinct_users_count"], int)
        assert isinstance(float(first_week["not_rollbacked_deposit_amount"]), float)
        assert isinstance(float(first_week["not_rollbacked_withdraw_amount"]), float)
        assert isinstance(first_week["transactions_count"], int)
        assert isinstance(first_week["not_rollbacked_transactions_count"], int)

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_weeks_order(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        for i in range(len(data) - 1):
            current_week = data[i]
            next_week = data[i + 1]

            current_start = datetime.fromisoformat(current_week["start_date"]).date()
            next_start = datetime.fromisoformat(next_week["start_date"]).date()

            expected_next_start = current_start - timedelta(days=7)
            assert next_start == expected_next_start

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_with_empty_data(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        for week in data:
            assert week["registered_users_count"] == 0
            assert week["deposit_distinct_users_count"] == 0
            assert week["transactions_count"] == 0
            assert week["not_rollbacked_transactions_count"] == 0

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_data_correctness(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        current_week = data[0]

        assert (
            current_week["not_rollbacked_transactions_count"]
            <= current_week["transactions_count"]
        )

        assert (
            current_week["deposit_distinct_users_count"]
            <= current_week["registered_users_count"]
        )

        assert float(current_week["not_rollbacked_deposit_amount"]) >= 0
        assert float(current_week["not_rollbacked_withdraw_amount"]) <= 0

    @pytest.mark.asyncio
    async def test_weekly_analytics_weeks_count(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 52

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_date_ranges(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        for week in data:
            start_date = datetime.fromisoformat(week["start_date"]).date()
            end_date = datetime.fromisoformat(week["end_date"]).date()

            assert (end_date - start_date).days == 6

            assert start_date.weekday() == 0
            assert end_date.weekday() == 6
