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
from .coordinator import O2Allowance, O2Coordinator, O2Data


@dataclass(frozen=True, kw_only=True)
class O2SensorDescription(SensorEntityDescription):
    """Describes an O2 UK sensor."""

    value_fn: Callable[[O2Data], Any]


def _data_remaining(data: O2Data) -> float | str | None:
    return _allowance_remaining(data.data, gigabytes=True)


def _data_initial(data: O2Data) -> float | str | None:
    return _allowance_initial(data.data, gigabytes=True)


def _voice_remaining(data: O2Data) -> float | str | None:
    return _allowance_remaining(data.voice, gigabytes=False)


def _text_remaining(data: O2Data) -> float | str | None:
    return _allowance_remaining(data.text, gigabytes=False)


def _allowance_remaining(allowance: O2Allowance | None, *, gigabytes: bool) -> float | str | None:
    if allowance is None:
        return None
    if allowance.balance is None:
        return "unlimited"
    return allowance.balance / 1024 if gigabytes else allowance.balance


def _allowance_initial(allowance: O2Allowance | None, *, gigabytes: bool) -> float | str | None:
    if allowance is None or allowance.initial is None:
        return None
    return allowance.initial / 1024 if gigabytes else allowance.initial


def _data_used(data: O2Data) -> float | None:
    if data.data is None or data.data.balance is None or data.data.initial is None:
        return None
    used_mb = max(data.data.initial - data.data.balance, 0.0)
    return used_mb / 1024


def _voice_used(data: O2Data) -> float | None:
    return _used_minutes_or_texts(data.voice)


def _text_used(data: O2Data) -> float | None:
    return _used_minutes_or_texts(data.text)


def _used_minutes_or_texts(allowance: O2Allowance | None) -> float | None:
    if allowance is None or allowance.balance is None or allowance.initial is None:
        return None
    return max(allowance.initial - allowance.balance, 0.0)


def _reset_date(data: O2Data) -> datetime | None:
    if data.data is None:
        return None
    return data.data.expires


def _bill_amount(data: O2Data) -> float | None:
    return data.latest_bill_amount


def _bill_date(data: O2Data) -> datetime | None:
    return data.latest_bill_date


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
        value_fn=_data_initial,
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
        key="minutes_used",
        translation_key="minutes_used",
        icon="mdi:phone-outgoing",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_voice_used,
    ),
    O2SensorDescription(
        key="texts_remaining",
        translation_key="texts_remaining",
        icon="mdi:message",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_text_remaining,
    ),
    O2SensorDescription(
        key="texts_used",
        translation_key="texts_used",
        icon="mdi:message-arrow-right",
        native_unit_of_measurement="messages",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_text_used,
    ),
    O2SensorDescription(
        key="allowance_reset",
        translation_key="allowance_reset",
        icon="mdi:calendar-range",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_reset_date,
    ),
    O2SensorDescription(
        key="latest_bill_amount",
        translation_key="latest_bill_amount",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=_bill_amount,
    ),
    O2SensorDescription(
        key="latest_bill_date",
        translation_key="latest_bill_date",
        icon="mdi:receipt",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_bill_date,
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="O2",
            model=coordinator.data.plan_subcategory if coordinator.data else None,
            serial_number=coordinator.data.msisdn if coordinator.data else None,
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)
        if self.entity_description.device_class == SensorDeviceClass.MONETARY and value is not None:
            self._attr_native_unit_of_measurement = (
                self.coordinator.data.latest_bill_currency or "GBP"
            )
        return value
