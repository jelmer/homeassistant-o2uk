"""Data update coordinator for the O2 UK integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import O2ApiClient, O2ApiError, O2AuthError
from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from .parser import O2Snapshot, parse_dashboard_html

_LOGGER = logging.getLogger(__name__)


class O2Coordinator(DataUpdateCoordinator[O2Snapshot]):
    """Fetches the ecare dashboard on a schedule and parses it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: O2ApiClient,
    ) -> None:
        interval_minutes = entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> O2Snapshot:
        try:
            html = await self.client.async_get_dashboard_html()
        except O2AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except O2ApiError as err:
            raise UpdateFailed(str(err)) from err

        return parse_dashboard_html(html)
