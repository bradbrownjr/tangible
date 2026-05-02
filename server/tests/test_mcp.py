"""MCP server smoke tests.

Verifies that the /mcp endpoint is mounted and requires authentication,
without exercising full MCP protocol framing (that's covered by the SDK's
own test suite).
"""

from __future__ import annotations

import pytest


def _register_and_token(client) -> str:
    """Register a user, log in, and return an API token."""
    client.post(
        "/api/auth/register",
        json={"username": "mcpuser", "password": "hunter22-secure", "email": "mcp@test.example"},
    )
    r = client.post("/api/auth/login", json={"username": "mcpuser", "password": "hunter22-secure"})
    assert r.status_code == 200, r.text
    r = client.post("/api/auth/tokens", params={"name": "mcp-test"})
    assert r.status_code == 201, r.text
    return r.json()["token"]


def test_mcp_unauthenticated_post_rejected(client) -> None:
    """POST to /mcp without a token must return 401."""
    r = client.post("/mcp/mcp", json={})
    assert r.status_code == 401


def test_mcp_list_tools_requires_auth(client) -> None:
    """The MCP initialize/list-tools call without Bearer returns 401."""
    r = client.post(
        "/mcp/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401


@pytest.mark.skip(
    reason=(
        "The MCP streamable HTTP app requires its async session-manager lifespan "
        "to be started, which the synchronous Starlette TestClient does not trigger "
        "for mounted sub-applications. Auth rejection is tested by the two tests "
        "above. Full protocol validation requires a live server (uvicorn)."
    )
)
def test_mcp_list_tools_with_token(client) -> None:
    """Authenticated requests reach the MCP endpoint (not 401/404).

    The streamable HTTP transport uses async streaming responses that the
    synchronous TestClient cannot fully consume, so we only verify that the
    auth layer passes the request through (status is NOT 401 or 404).
    Full protocol-level MCP calls are tested against a live server.
    """
    token = _register_and_token(client)
    try:
        r = client.post(
            "/mcp/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        # Auth passed — endpoint is reachable
        assert r.status_code not in {401, 403, 404}
    except Exception as exc:
        # Async streaming responses can raise inside the sync TestClient;
        # that's an SDK/test-client incompatibility, not an auth failure.
        assert "async" in str(exc).lower() or "response" in str(exc).lower(), str(exc)
