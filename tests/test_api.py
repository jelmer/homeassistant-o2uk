"""Tests for the cookie-paste API client."""

from __future__ import annotations

import gzip
import os

import pytest
from aiohttp import ClientSession, web

from custom_components.o2uk import api as api_module
from custom_components.o2uk.api import O2ApiClient, O2AuthError, parse_cookie_string

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ecare_home.html.gz")


def _load_fixture() -> str:
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as f:
        return f.read()


def test_parse_cookie_string_basic() -> None:
    cookies = parse_cookie_string("foo=bar; baz=qux")
    assert cookies == {"foo": "bar", "baz": "qux"}


def test_parse_cookie_string_with_header_prefix() -> None:
    cookies = parse_cookie_string("Cookie: foo=bar; baz=qux")
    assert cookies == {"foo": "bar", "baz": "qux"}


def test_parse_cookie_string_handles_newlines() -> None:
    cookies = parse_cookie_string("foo=bar\nbaz=qux")
    assert cookies == {"foo": "bar", "baz": "qux"}


def test_parse_cookie_string_empty() -> None:
    assert parse_cookie_string("") == {}
    assert parse_cookie_string("   \n  ") == {}


@pytest.fixture
async def server(monkeypatch, aiohttp_server):
    """Spin up a fake ecare host and rewrite DASHBOARD_URL to point at it."""
    behaviour: dict = {"require_cookie": True}
    fixture_html = _load_fixture()

    async def ecare_home(request: web.Request) -> web.Response:
        if behaviour["require_cookie"] and not request.cookies.get("session"):
            # Simulate the dashboard redirecting to sign-in.
            return web.Response(
                status=200,
                text="<html>daVinciResponseForm</html>",
                content_type="text/html",
            )
        return web.Response(status=200, text=fixture_html, content_type="text/html")

    app = web.Application()
    app.router.add_get("/ecare/home", ecare_home)
    srv = await aiohttp_server(app)

    base = str(srv.make_url("/ecare/home"))
    monkeypatch.setattr(api_module, "DASHBOARD_URL", base)
    return srv, behaviour


async def test_get_dashboard_succeeds_with_cookies(server) -> None:
    async with ClientSession() as s:
        client = O2ApiClient(s, {"session": "valid"})
        html = await client.async_get_dashboard_html()
        assert "__next_f" in html
        assert "07700900000" in html  # sanitized msisdn from fixture


async def test_get_dashboard_raises_auth_when_cookies_missing(server) -> None:
    async with ClientSession() as s:
        client = O2ApiClient(s, {})
        with pytest.raises(O2AuthError):
            await client.async_get_dashboard_html()


async def test_get_dashboard_raises_auth_when_cookies_invalid(server) -> None:
    async with ClientSession() as s:
        client = O2ApiClient(s, {"unrelated": "value"})
        with pytest.raises(O2AuthError):
            await client.async_get_dashboard_html()
