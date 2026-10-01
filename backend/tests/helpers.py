"""Test helpers shared across the HTTP-level test modules."""

from __future__ import annotations

from httpx import AsyncClient

TEST_USERNAME = "owner"
TEST_PASSWORD = "correct-horse-battery-staple"


async def login(
    client: AsyncClient,
    username: str = TEST_USERNAME,
    password: str = TEST_PASSWORD,
):
    return await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
