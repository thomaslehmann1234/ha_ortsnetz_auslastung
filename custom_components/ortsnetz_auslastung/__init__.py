from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_API_URL, CONF_GRID_FREQUENCY_ENTITY, CONF_L1_ENTITY, CONF_L2_ENTITY, CONF_L3_ENTITY, CONF_LATITUDE, CONF_LONGITUDE, CONF_PLANT_CAPACITY_KWP, CONF_PV_FORECAST_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _value(hass: HomeAssistant, entity_id: str) -> float | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Update existing entries to the current integration name."""
    if entry.version < 3:
        data = dict(entry.data)
        data.pop("token", None)
        hass.config_entries.async_update_entry(entry, title="Ortsnetz-Auslastung", data=data, version=3)
    return True


async def _send(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Options override the initial setup data.
    data = {**entry.data, **entry.options}
    values = [_value(hass, data[key]) for key in (CONF_L1_ENTITY, CONF_L2_ENTITY, CONF_L3_ENTITY)]
    if any(value is None for value in values):
        _LOGGER.warning("Spannungssensor für Ortsnetz-Auslastung ist nicht verfügbar")
        return
    payload = {
        "observed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "latitude": data[CONF_LATITUDE], "longitude": data[CONF_LONGITUDE],
        "l1_v": values[0], "l2_v": values[1], "l3_v": values[2],
    }
    if data.get(CONF_PLANT_CAPACITY_KWP) is not None:
        payload[CONF_PLANT_CAPACITY_KWP] = data[CONF_PLANT_CAPACITY_KWP]
    forecast_entity = data.get(CONF_PV_FORECAST_ENTITY)
    if forecast_entity:
        forecast_kwh = _value(hass, forecast_entity)
        if forecast_kwh is None:
            _LOGGER.warning("PV-Forecast-Sensor für Ortsnetz-Auslastung ist nicht verfügbar")
        else:
            payload["pv_forecast_kwh"] = forecast_kwh
    frequency_entity = data.get(CONF_GRID_FREQUENCY_ENTITY)
    if frequency_entity:
        frequency_hz = _value(hass, frequency_entity)
        if frequency_hz is None:
            _LOGGER.warning("Netzfrequenz-Sensor für Ortsnetz-Auslastung ist nicht verfügbar")
        else:
            payload["grid_frequency_hz"] = frequency_hz
    url = f"{data[CONF_API_URL].rstrip('/')}/v1/measurements"
    session = async_get_clientsession(hass)
    for attempt in range(2):
        try:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status < 300:
                    return
                _LOGGER.warning("Ortsnetz-API antwortete mit HTTP %s", response.status)
        except (asyncio.TimeoutError, OSError) as error:
            _LOGGER.warning("Ortsnetz-Messung konnte nicht gesendet werden: %s", error)
        if attempt == 0:
            await asyncio.sleep(5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def scheduled_send(_: datetime) -> None:
        """Send from Home Assistant's event loop at each interval."""
        await _send(hass, entry)

    cancel = async_track_time_interval(hass, scheduled_send, timedelta(minutes=5))
    hass.data[DOMAIN][entry.entry_id] = cancel
    hass.async_create_task(_send(hass, entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cancel = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if cancel:
        cancel()
    return True
