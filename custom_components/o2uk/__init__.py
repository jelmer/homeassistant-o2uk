"""The O2 UK integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import O2ApiClient, O2ApiError, O2AuthError
from .const import CONF_COOKIES, CONFIG_VERSION, DOMAIN
from .coordinator import O2Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up O2 UK from a config entry."""
    session = async_get_clientsession(hass)
    cookies = entry.data.get(CONF_COOKIES) or {}
    if isinstance(cookies, str):
        # Migrate older entries that stored the raw string.
        from .api import parse_cookie_string

        cookies = parse_cookie_string(cookies)

    client = O2ApiClient(session, cookies)
    coordinator = O2Coordinator(hass, entry, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except O2AuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except O2ApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version > CONFIG_VERSION:
        _LOGGER.error("Cannot downgrade O2 UK config entry from version %s", entry.version)
        return False
    return True
