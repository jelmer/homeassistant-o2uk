"""Constants for the O2 UK integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "o2uk"
CONFIG_VERSION: Final = 1

DEFAULT_NAME: Final = "O2 UK"
DEFAULT_SCAN_INTERVAL_MINUTES: Final = 30
MIN_SCAN_INTERVAL_MINUTES: Final = 5

CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

LOGIN_URL: Final = "https://identity.o2.co.uk/auth/password_o2"
LOGIN_RETURN_URL: Final = "https://accounts.o2.co.uk/?checkproduct=true"
ACCOUNT_BASE_URL: Final = "https://mymobile2.o2.co.uk"
ACCOUNT_HOME_URL: Final = f"{ACCOUNT_BASE_URL}/"
ALLOWANCES_URL: Final = (
    f"{ACCOUNT_BASE_URL}/web/guest/account"
    "?p_p_id=O2UKAccountPortlet_INSTANCE_0ssTPnzpDk4K"
    "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
    "&p_p_resource_id=getBoltOnsAndCurrentTariff"
    "&p_p_cacheability=cacheLevelPage"
)
BILLS_URL: Final = (
    f"{ACCOUNT_BASE_URL}/web/guest/account"
    "?p_p_id=O2UKAccountPortlet_INSTANCE_0ssTPnzpDk4K"
    "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
    "&p_p_resource_id=getBills"
    "&p_p_cacheability=cacheLevelPage"
)

USER_AGENT: Final = "homeassistant-o2uk/0.1.0"

# Session lifetime (45 minutes) – the O2 portal session expires not long after.
SESSION_LIFETIME_SECONDS: Final = 45 * 60
