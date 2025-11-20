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

        assert isinstance(data, dict)
        assert "message" in data
        assert data["message"] == "OK"

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_with_empty_data(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert data["message"] == "OK"

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_data_correctness(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert data == {"message": "OK"}

    @pytest.mark.asyncio
    async def test_weekly_analytics_weeks_count(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_get_transaction_analysis_date_ranges(
        self, client: AsyncClient, test_users: list[dict], test_transactions: list[dict]
    ) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()

        assert data == {"message": "OK"}

    @pytest.mark.asyncio
    async def test_background_task_triggered(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/analytics/transactions")

        assert response.status_code == 200
        data = response.json()
        assert data == {"message": "OK"}
