import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestTransactionsAPI:
    @pytest_asyncio.fixture
    async def created_user(self, client: AsyncClient) -> dict:
        response = await client.post(
            "/api/v1/users", json={"email": "transactions_test_user@example.com"}
        )
        return response.json()

    @pytest_asyncio.fixture
    async def blocked_user(self, client: AsyncClient) -> dict:
        response = await client.post(
            "/api/v1/users", json={"email": "blocked_transactions_user@example.com"}
        )
        user = response.json()

        await client.patch(f"/api/v1/users/{user['id']}", json={"status": "BLOCKED"})
        return user

    @pytest.mark.asyncio
    async def test_create_deposit_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.post(
            f"/api/v1/transactions/{created_user["id"]}",
            json={"currency": "USD", "amount": 100.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == created_user["id"]
        assert data["currency"] == "USD"
        assert data["amount"] == 100.0
        assert data["status"] == "PROCESSED"

    @pytest.mark.asyncio
    async def test_create_withdrawal_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 50.0},
        )

        response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": -50.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == -50.0

    @pytest.mark.asyncio
    async def test_create_transaction_insufficient_funds(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": -50.0},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_transaction_blocked_user(
        self, client: AsyncClient, blocked_user: dict
    ) -> None:
        response = await client.post(
            f"/api/v1/transactions/{blocked_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_transaction_nonexistent_user(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/transactions/99999", json={"currency": "USD", "amount": 100.0}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_currency(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "INVALID", "amount": 100.0},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_transaction_zero_amount(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 0.0},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_user_id(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/transactions/-1", json={"currency": "USD", "amount": 100.0}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_user_transactions(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )

        response = await client.get(f"/api/v1/transactions?user_id={created_user['id']}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(transaction["user_id"] == created_user["id"] for transaction in data)

    @pytest.mark.asyncio
    async def test_get_all_transactions(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )

        response = await client.get("/api/v1/transactions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_transactions_nonexistent_user(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/transactions?user_id=99999")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_rollback_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        deposit_response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )
        transaction = deposit_response.json()

        response = await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/{created_user['id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ROLLBACKED"

    @pytest.mark.asyncio
    async def test_rollback_already_rollbacked_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        deposit_response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )
        transaction = deposit_response.json()

        await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/{created_user['id']}"
        )

        response = await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/{created_user['id']}"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.patch(
            f"/api/v1/transactions/99999/users/{created_user['id']}"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rollback_other_user_transaction(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        another_user_response = await client.post(
            "/api/v1/users", json={"email": "another_user@example.com"}
        )
        another_user = another_user_response.json()

        deposit_response = await client.post(
            f"/api/v1/transactions/{another_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )
        transaction = deposit_response.json()

        response = await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/{created_user['id']}"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rollback_transaction_blocked_user(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        deposit_response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )
        transaction = deposit_response.json()

        await client.patch(
            f"/api/v1/users/{created_user['id']}", json={"status": "BLOCKED"}
        )

        response = await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/{created_user['id']}"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rollback_invalid_transaction_id(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.patch(
            f"/api/v1/transactions/-1/users/{created_user['id']}"
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rollback_invalid_user_id(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        deposit_response = await client.post(
            f"/api/v1/transactions/{created_user['id']}",
            json={"currency": "USD", "amount": 100.0},
        )
        transaction = deposit_response.json()

        response = await client.patch(
            f"/api/v1/transactions/{transaction['id']}/users/-1"
        )

        assert response.status_code == 422
