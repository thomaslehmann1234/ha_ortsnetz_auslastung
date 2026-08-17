"""Status entity for Ortsnetz-Auslastung."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import status_signal

_LABELS = {"green": "Grün", "yellow": "Gelb", "red": "Rot"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the single lightweight status sensor."""
    async_add_entities([VoltageStatusSensor(entry)])


class VoltageStatusSensor(SensorEntity):
    """Expose the last server-evaluated voltage status."""

    _attr_has_entity_name = True
    _attr_name = "Netzspannungsstatus"
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_voltage_status"
        self._entry = entry
        self._status: dict[str, str] | None = None

    @property
    def native_value(self) -> str | None:
        if self._status is None:
            return None
        return _LABELS[self._status["overall"]]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._status is None:
            return None
        return {
            "L1": _LABELS[self._status["l1"]],
            "L2": _LABELS[self._status["l2"]],
            "L3": _LABELS[self._status["l3"]],
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, status_signal(self._entry.entry_id), self._async_update_status)
        )

    def _async_update_status(self, status: dict[str, str]) -> None:
        self._status = status
        self.async_write_ha_state()
