from httpx import AsyncClient


async def test_auth_register_login_me(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "role": "user",
        },
    )
    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["username"] == "alice"
    assert registered["role"] == "user"

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )
    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert token_payload["token_type"] == "bearer"
    assert token_payload["access_token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    me = me_response.json()
    assert me["username"] == "alice"
    assert me["role"] == "user"
