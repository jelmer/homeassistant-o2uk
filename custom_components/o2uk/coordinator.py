"""Data update coordinator for the O2 UK integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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

_LOGGER = logging.getLogger(__name__)


@dataclass
class O2Allowance:
    """Allowance for a single category (data/voice/text)."""

    balance: float | None  # remaining; None means unlimited
    initial: float | None
    unit: str | None
    expires: datetime | None


@dataclass
class O2Data:
    """Structured snapshot of the account."""

    msisdn: str | None
    plan_name: str | None
    plan_subcategory: str | None
    data: O2Allowance | None
    voice: O2Allowance | None
    text: O2Allowance | None
    latest_bill_amount: float | None
    latest_bill_date: datetime | None
    latest_bill_currency: str | None
    raw: dict[str, Any]


class O2Coordinator(DataUpdateCoordinator[O2Data]):
    """Fetches O2 UK account data on a schedule."""

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

    async def _async_update_data(self) -> O2Data:
        try:
            allowances = await self.client.async_get_allowances()
            bills: dict[str, Any] | None
            try:
                bills = await self.client.async_get_bills()
            except O2ApiError as err:
                # Bills are optional – PAYG accounts may not expose them.
                _LOGGER.debug("Bills endpoint unavailable: %s", err)
                bills = None
        except O2AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except O2ApiError as err:
            raise UpdateFailed(str(err)) from err

        return _parse(allowances, bills)


def _parse(allowances: dict[str, Any], bills: dict[str, Any] | None) -> O2Data:
    tariff = allowances.get("tariffVM") or {}
    balances = allowances.get("allowancesBalance") or {}

    return O2Data(
        msisdn=tariff.get("number"),
        plan_name=tariff.get("name"),
        plan_subcategory=tariff.get("subcategory"),
        data=_parse_allowance(balances.get("data")),
        voice=_parse_allowance(balances.get("voice")),
        text=_parse_allowance(balances.get("text")),
        latest_bill_amount=_parse_bill_amount(bills),
        latest_bill_date=_parse_bill_date(bills),
        latest_bill_currency=_parse_bill_currency(bills),
        raw={"allowances": allowances, "bills": bills},
    )


def _parse_allowance(items: list[dict[str, Any]] | None) -> O2Allowance | None:
    if not items:
        return None
    item = items[0]

    balance = item.get("balance")
    initial = item.get("initialBalance") or item.get("allowance")
    unit = item.get("unit") or item.get("uom")
    expires = None
    details = item.get("details") or []
    if details:
        expires_raw = details[0].get("expiresDate")
        if expires_raw:
            try:
                expires = datetime.strptime(expires_raw, "%d %B %Y")
            except ValueError:
                _LOGGER.debug("Could not parse expiresDate: %s", expires_raw)

    return O2Allowance(
        balance=_to_float(balance),
        initial=_to_float(initial),
        unit=unit,
        expires=expires,
    )


def _parse_bill_amount(bills: dict[str, Any] | None) -> float | None:
    bill = _latest_bill(bills)
    if bill is None:
        return None
    return _to_float(bill.get("amount") or bill.get("totalAmount"))


def _parse_bill_date(bills: dict[str, Any] | None) -> datetime | None:
    bill = _latest_bill(bills)
    if bill is None:
        return None
    raw = bill.get("billDate") or bill.get("date") or bill.get("issueDate")
    if not raw:
        return None
    for fmt in ("%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    _LOGGER.debug("Could not parse bill date: %s", raw)
    return None


def _parse_bill_currency(bills: dict[str, Any] | None) -> str | None:
    bill = _latest_bill(bills)
    if bill is None:
        return None
    return bill.get("currency") or "GBP"


def _latest_bill(bills: dict[str, Any] | None) -> dict[str, Any] | None:
    if not bills:
        return None
    candidates = (
        bills.get("bills")
        or bills.get("billList")
        or bills.get("billHistoryList")
        or bills.get("data")
    )
    if isinstance(candidates, list) and candidates:
        return candidates[0]
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
