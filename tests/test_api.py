"""Tests for the O2ApiClient against a fake aiohttp server."""

from __future__ import annotations

import pytest
from aiohttp import ClientSession, web

from custom_components.o2uk import api as api_module
from custom_components.o2uk.api import O2ApiClient, O2ApiError, O2AuthError

HOME_PAGE_HTML = """
<html><head><script>
  Liferay.authToken = 'csrf-token-xyz';
</script></head><body>ok</body></html>
"""

ALLOWANCE_JSON = {
    "tariffVM": {"number": "447700900123", "name": "Plan", "subcategory": "PAYM"},
    "allowancesBalance": {
        "data": [
            {
                "balance": 1024,
                "initialBalance": 2048,
                "unit": "MB",
                "details": [{"expiresDate": "15 May 2026"}],
            }
        ],
        "voice": [],
        "text": [],
    },
}


def _make_app(behaviour: dict) -> web.Application:
    """Build an aiohttp app that mimics the My O2 endpoints.

    behaviour controls per-test branching:
      - login_status: HTTP status to return from /auth/password_o2
      - login_location: Location header for the redirect
    """
    app = web.Application()

    async def login(request: web.Request) -> web.Response:
        await request.post()
        return web.Response(
            status=behaviour.get("login_status", 303),
            headers={"Location": behaviour.get("login_location", "/ok")},
        )

    async def home(_request: web.Request) -> web.Response:
        return web.Response(
            text=behaviour.get("home_html", HOME_PAGE_HTML),
            content_type="text/html",
        )

    async def allowances(request: web.Request) -> web.Response:
        if request.headers.get("X-Csrf-Token") != "csrf-token-xyz":
            return web.Response(status=403)
        return web.json_response(ALLOWANCE_JSON)

    app.router.add_post("/auth/password_o2", login)
    app.router.add_get("/", home)
    app.router.add_post("/web/guest/account", allowances)
    return app


@pytest.fixture
async def server(monkeypatch, aiohttp_server):
    """Start a fake server and point the client at it."""
    behaviour: dict = {}
    app = _make_app(behaviour)
    srv = await aiohttp_server(app)

    base = str(srv.make_url("")).rstrip("/")
    monkeypatch.setattr(api_module, "LOGIN_URL", f"{base}/auth/password_o2")
    monkeypatch.setattr(api_module, "LOGIN_RETURN_URL", f"{base}/ok")
    monkeypatch.setattr(api_module, "ACCOUNT_HOME_URL", f"{base}/")
    monkeypatch.setattr(api_module, "ALLOWANCES_URL", f"{base}/web/guest/account")
    monkeypatch.setattr(api_module, "BILLS_URL", f"{base}/web/guest/account")

    return srv, behaviour


async def test_login_success(server) -> None:
    srv, behaviour = server
    async with ClientSession() as session:
        client = O2ApiClient(session, "user", "pw")
        await client.async_login()


async def test_login_invalid_credentials(server) -> None:
    srv, behaviour = server
    behaviour["login_location"] = "/ok?error=invalid"
    async with ClientSession() as session:
        client = O2ApiClient(session, "user", "pw")
        with pytest.raises(O2AuthError):
            await client.async_login()


async def test_login_unexpected_status(server) -> None:
    srv, behaviour = server
    behaviour["login_status"] = 500
    async with ClientSession() as session:
        client = O2ApiClient(session, "user", "pw")
        with pytest.raises(O2AuthError):
            await client.async_login()


async def test_get_allowances(server) -> None:
    async with ClientSession() as session:
        client = O2ApiClient(session, "user", "pw")
        await client.async_login()
        result = await client.async_get_allowances()
        assert result["tariffVM"]["number"] == "447700900123"


async def test_csrf_missing_raises(server) -> None:
    srv, behaviour = server
    behaviour["home_html"] = "<html><body>no token here</body></html>"
    async with ClientSession() as session:
        client = O2ApiClient(session, "user", "pw")
        await client.async_login()
        with pytest.raises(O2ApiError):
            await client.async_get_allowances()
