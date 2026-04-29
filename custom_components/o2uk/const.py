"""Constants for the O2 UK integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "o2uk"
CONFIG_VERSION: Final = 1

DEFAULT_NAME: Final = "O2 UK"
DEFAULT_SCAN_INTERVAL_MINUTES: Final = 30
MIN_SCAN_INTERVAL_MINUTES: Final = 5

CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

DASHBOARD_URL: Final = "https://www.o2.co.uk/ecare/home"

USER_AGENT: Final = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

STORAGE_FILENAME: Final = "o2uk_session.json"
