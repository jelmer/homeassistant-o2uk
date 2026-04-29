"""Config and options flow for the O2 UK integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import O2ApiClient, O2ApiError, O2AuthError, parse_cookie_string
from .const import (
    CONF_COOKIES,
    CONF_SCAN_INTERVAL_MINUTES,
    CONFIG_VERSION,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema({vol.Required(CONF_COOKIES): str})


async def _validate_cookies(hass, raw_cookies: str) -> dict[str, str]:
    cookies = parse_cookie_string(raw_cookies)
    if not cookies:
        raise O2AuthError("No cookies parsed from input")

    session = async_get_clientsession(hass)
    client = O2ApiClient(session, cookies)
    # Will raise O2AuthError if the dashboard redirects to sign-in.
    await client.async_get_dashboard_html()
    return cookies


class O2UKConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = CONFIG_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                cookies = await _validate_cookies(self.hass, user_input[CONF_COOKIES])
            except O2AuthError:
                errors["base"] = "invalid_cookies"
            except O2ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating O2 UK cookies")
                errors["base"] = "unknown"
            else:
                # Use a stable identifier from the cookies if we can find
                # one; otherwise just allow a single entry per HA instance.
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="O2 UK",
                    data={CONF_COOKIES: cookies},
                )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                cookies = await _validate_cookies(self.hass, user_input[CONF_COOKIES])
            except O2AuthError:
                errors["base"] = "invalid_cookies"
            except O2ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating O2 UK cookies")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_COOKIES: cookies},
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=USER_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return O2UKOptionsFlow(config_entry)


class O2UKOptionsFlow(OptionsFlow):
    """Options flow: poll interval, plus a way to refresh cookies."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            new_data = dict(self._entry.data)
            raw_cookies = user_input.get(CONF_COOKIES, "").strip()
            if raw_cookies:
                try:
                    new_data[CONF_COOKIES] = await _validate_cookies(self.hass, raw_cookies)
                except O2AuthError:
                    errors["base"] = "invalid_cookies"
                except O2ApiError:
                    errors["base"] = "cannot_connect"

            if not errors:
                self.hass.config_entries.async_update_entry(self._entry, data=new_data)
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL_MINUTES: user_input[CONF_SCAN_INTERVAL_MINUTES]},
                )

        current_interval = self._entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=current_interval): vol.All(
                    int, vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)
                ),
                vol.Optional(CONF_COOKIES): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
