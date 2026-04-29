"""Sensor entities for the O2 UK integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import O2Coordinator
from .parser import O2Snapshot


@dataclass(frozen=True, kw_only=True)
class O2SensorDescription(SensorEntityDescription):
    """Describes an O2 UK sensor."""

    value_fn: Callable[[O2Snapshot], Any]


def _data_remaining(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("data")
    return a.remaining if a and not a.unlimited else None


def _data_used(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("data")
    return a.used if a else None


def _data_allowance(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("data")
    return a.initial if a and not a.unlimited else None


def _voice_used(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("voice")
    return a.used if a else None


def _voice_remaining(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("voice")
    return a.remaining if a and not a.unlimited else None


def _sms_used(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("sms")
    return a.used if a else None


def _sms_remaining(snap: O2Snapshot) -> float | None:
    a = snap.allowances.get("sms")
    return a.remaining if a and not a.unlimited else None


def _reset_date(snap: O2Snapshot) -> datetime | None:
    return snap.reset_date


def _spend_cap(snap: O2Snapshot) -> float | None:
    return snap.spend_cap


def _monthly_charge(snap: O2Snapshot) -> float | None:
    return snap.tariff_monthly_charge


SENSORS: tuple[O2SensorDescription, ...] = (
    O2SensorDescription(
        key="data_remaining",
        translation_key="data_remaining",
        icon="mdi:chart-donut",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_data_remaining,
    ),
    O2SensorDescription(
        key="data_used",
        translation_key="data_used",
        icon="mdi:download",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=_data_used,
    ),
    O2SensorDescription(
        key="data_allowance",
        translation_key="data_allowance",
        icon="mdi:gauge",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        suggested_display_precision=2,
        value_fn=_data_allowance,
    ),
    O2SensorDescription(
        key="minutes_used",
        translation_key="minutes_used",
        icon="mdi:phone-outgoing",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_voice_used,
    ),
    O2SensorDescription(
        key="minutes_remaining",
        translation_key="minutes_remaining",
        icon="mdi:phone",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_voice_remaining,
    ),
    O2SensorDescription(
        key="texts_used",
        translation_key="texts_used",
        icon="mdi:message-arrow-right",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_sms_used,
    ),
    O2SensorDescription(
        key="texts_remaining",
        translation_key="texts_remaining",
        icon="mdi:message",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sms_remaining,
    ),
    O2SensorDescription(
        key="allowance_reset",
        translation_key="allowance_reset",
        icon="mdi:calendar-range",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_reset_date,
    ),
    O2SensorDescription(
        key="spend_cap",
        translation_key="spend_cap",
        icon="mdi:currency-gbp",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
        value_fn=_spend_cap,
    ),
    O2SensorDescription(
        key="monthly_charge",
        translation_key="monthly_charge",
        icon="mdi:cash-multiple",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
        value_fn=_monthly_charge,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up O2 UK sensors."""
    coordinator: O2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(O2Sensor(coordinator, entry, description) for description in SENSORS)


class O2Sensor(CoordinatorEntity[O2Coordinator], SensorEntity):
    """A single O2 UK sensor."""

    entity_description: O2SensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: O2Coordinator,
        entry: ConfigEntry,
        description: O2SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        msisdn = coordinator.data.msisdn if coordinator.data else None
        product_type = coordinator.data.product_type if coordinator.data else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="O2",
            model=product_type,
            serial_number=msisdn,
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
