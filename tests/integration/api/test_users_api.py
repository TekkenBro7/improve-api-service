import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestUsersAPI:
    @pytest_asyncio.fixture
    async def created_user(self, client: AsyncClient) -> dict:
        response = await client.post(
            "/api/v1/users", json={"email": "test_api_user@example.com"}
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_create_user_success(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "new_user@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new_user@example.com"
        assert "id" in data
        assert "status" in data
        assert data["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.post(
            "/api/v1/users", json={"email": "test_api_user@example.com"}
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_user_empty_email(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/users", json={"email": "   "})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_all_users(self, client: AsyncClient, created_user: dict) -> None:
        response = await client.get("/api/v1/users")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["id"] == created_user["id"] for user in data)

    @pytest.mark.asyncio
    async def test_get_users_by_id(self, client: AsyncClient, created_user: dict) -> None:
        response = await client.get(f"/api/v1/users?user_id={created_user['id']}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == created_user["id"]
        assert data[0]["email"] == created_user["email"]

    @pytest.mark.asyncio
    async def test_get_users_by_email(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.get(f"/api/v1/users?email={created_user['email']}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["email"] == created_user["email"]

    @pytest.mark.asyncio
    async def test_get_users_by_status(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.get("/api/v1/users?user_status=ACTIVE")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(user["status"] == "ACTIVE" for user in data)

    @pytest.mark.asyncio
    async def test_get_users_by_nonexistent_id(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users?user_id=99999")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_users_with_multiple_filters(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.get(
            f"/api/v1/users?user_id={created_user['id']}&email={created_user['email']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created_user["id"]
        assert data[0]["email"] == created_user["email"]

    @pytest.mark.asyncio
    async def test_update_user_status_to(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.patch(
            f"/api/v1/users/{created_user['id']}", json={"status": "BLOCKED"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_user["id"]
        assert data["status"] == "BLOCKED"

    @pytest.mark.asyncio
    async def test_update_user_status_already_blocked(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        await client.patch(
            f"/api/v1/users/{created_user['id']}", json={"status": "BLOCKED"}
        )

        response = await client.patch(
            f"/api/v1/users/{created_user['id']}", json={"status": "BLOCKED"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_user_status_nonexistent_user(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/users/99999", json={"status": "BLOCKED"})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_status_invalid_user_id(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/users/-1", json={"status": "BLOCKED"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_user_status_invalid_status(
        self, client: AsyncClient, created_user: dict
    ) -> None:
        response = await client.patch(
            f"/api/v1/users/{created_user['id']}", json={"status": "INVALID_STATUS"}
        )

        assert response.status_code == 422
