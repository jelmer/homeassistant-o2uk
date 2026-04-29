"""Async client for the My O2 (UK) self-service portal.

The integration relies on undocumented endpoints used by the My O2 web
portal. There is no official public API. Two pieces are needed:

1. ``identity.o2.co.uk/auth/password_o2`` – form-based login that issues
   a session cookie when credentials are valid. A successful login
   replies with ``303`` and a ``Location`` header pointing back at the
   portal; an invalid login redirects to a URL containing ``error``.
2. ``mymobile2.o2.co.uk`` – Liferay-backed portal that exposes JSON
   "resource" endpoints. These require a CSRF token (``Liferay.authToken``)
   embedded in the home page HTML and the session cookies established by
   the login step.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    ACCOUNT_HOME_URL,
    ALLOWANCES_URL,
    BILLS_URL,
    LOGIN_RETURN_URL,
    LOGIN_URL,
    SESSION_LIFETIME_SECONDS,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_CSRF_RE = re.compile(r"Liferay\.authToken\s*=\s*'([^']+)'")


class O2ApiError(Exception):
    """Generic API failure (transient: network, 5xx, parsing)."""


class O2AuthError(O2ApiError):
    """Authentication failed – credentials are invalid or expired."""


class O2ApiClient:
    """Async client for the My O2 web portal."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._session_birth: float = 0.0
        self._csrf_token: str | None = None

    @property
    def username(self) -> str:
        return self._username

    async def async_login(self) -> None:
        """Establish a portal session."""
        try:
            async with self._session.post(
                LOGIN_URL,
                data={
                    "username": self._username,
                    "password": self._password,
                    "sentTo": LOGIN_RETURN_URL,
                },
                headers={"User-Agent": USER_AGENT},
                allow_redirects=False,
            ) as resp:
                if resp.status != 303:
                    raise O2AuthError(f"Unexpected login status {resp.status}")
                location = resp.headers.get("Location", "")
                if not location or "error" in location.lower():
                    raise O2AuthError("Invalid credentials")
        except ClientError as err:
            raise O2ApiError(f"Network error during login: {err}") from err

        self._session_birth = time.monotonic()
        self._csrf_token = None
        _LOGGER.debug("O2 UK session established for %s", self._username)

    async def async_get_allowances(self) -> dict[str, Any]:
        """Return the raw allowances/tariff JSON for the account."""
        return await self._post_json(ALLOWANCES_URL)

    async def async_get_bills(self) -> dict[str, Any]:
        """Return the raw bills JSON for the account."""
        return await self._post_json(BILLS_URL)

    async def _post_json(self, url: str) -> dict[str, Any]:
        await self._ensure_session()
        csrf = await self._get_csrf_token()

        try:
            async with self._session.post(
                url,
                headers={
                    "X-Csrf-Token": csrf,
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                },
            ) as resp:
                if resp.status in (401, 403):
                    self._invalidate_session()
                    raise O2AuthError(f"Portal rejected request ({resp.status}); session expired")
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except ClientResponseError as err:
            self._invalidate_session()
            raise O2ApiError(f"HTTP error {err.status} for {url}") from err
        except ClientError as err:
            raise O2ApiError(f"Network error for {url}: {err}") from err
        except ValueError as err:
            raise O2ApiError(f"Invalid JSON from {url}: {err}") from err

    async def _ensure_session(self) -> None:
        if (
            self._session_birth == 0.0
            or time.monotonic() - self._session_birth > SESSION_LIFETIME_SECONDS
        ):
            await self.async_login()

    async def _get_csrf_token(self) -> str:
        if self._csrf_token is not None:
            return self._csrf_token

        try:
            async with self._session.get(
                ACCOUNT_HOME_URL,
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                resp.raise_for_status()
                body = await resp.text()
        except ClientError as err:
            raise O2ApiError(f"Failed to load portal home page: {err}") from err

        match = _CSRF_RE.search(body)
        if not match:
            self._invalidate_session()
            raise O2ApiError("Could not locate CSRF token on portal home page")

        token = match.group(1)
        self._csrf_token = token
        return token

    def _invalidate_session(self) -> None:
        self._session_birth = 0.0
        self._csrf_token = None
