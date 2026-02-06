from httpx import AsyncClient


async def test_users_crud(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/users",
        json={"name": "Ada Lovelace", "email": "ada@example.com"},
    )
    assert create_response.status_code == 405

    list_response = await client.get("/api/v1/users")
    assert list_response.status_code == 200
