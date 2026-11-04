"""Tests for stopping transmissions when the entry is unloaded."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.ortsnetz_auslastung.const import DOMAIN

URL = "https://example.test/v1/measurements"
OK = {"status": {"l1": "green", "l2": "green", "l3": "green", "overall": "green"}, "storage_recommendation": "none"}


async def _setup(hass, aioclient_mock, status=200, *, started=True, **extra_data):
    hass.state = CoreState.running if started else CoreState.starting
    for entity in ("sensor.l1", "sensor.l2", "sensor.l3"):
        hass.states.async_set(entity, 230)
    aioclient_mock.post(URL, status=status, json=OK)
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={
        "api_url": URL, "l1_entity": "sensor.l1", "l2_entity": "sensor.l2", "l3_entity": "sensor.l3",
        "latitude": 52.5, "longitude": 13.4, **extra_data,
    })
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    return entry


async def test_first_measurement_waits_for_started_and_includes_late_sensors(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, started=False,
                 grid_power_w_entity="sensor.grid_power", pv_forecast_entity="sensor.forecast",
                 plant_capacity_kwp=10)
    assert aioclient_mock.call_count == 0
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 0

    hass.states.async_set("sensor.grid_power", "-1500", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.forecast", "12.5", {"unit_of_measurement": "kWh"})
    hass.state = CoreState.running
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload["grid_power_w"] == -1500
    assert payload["pv_forecast_kwh"] == 12.5
    assert (payload["l1_v"], payload["l2_v"], payload["l3_v"]) == (230, 230, 230)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 2


async def test_unload_before_started_cancels_first_send_and_timer(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock, started=False)
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.state = CoreState.running
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=10))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 0


async def test_reload_before_started_registers_only_one_send_and_timer(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock, started=False)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 0
    hass.state = CoreState.running
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 1
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 2


async def test_setup_sends_and_timer_sends(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 2


async def test_unload_stops_timer(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=10, seconds=1))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 1


async def test_unload_cancels_pending_retry(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock, status=500)
    assert aioclient_mock.call_count == 1  # first attempt failed, now waiting before the retry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await asyncio.sleep(5.3)
    assert aioclient_mock.call_count == 1


# The entry stays loaded after a failed unload, so its timer is expected to linger.
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_failed_unload_keeps_sending(hass, aioclient_mock, expected_lingering_timers):
    entry = await _setup(hass, aioclient_mock)
    with patch.object(hass.config_entries, "async_unload_platforms", return_value=False):
        assert not await hass.config_entries.async_unload(entry.entry_id)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 2


async def test_reload_runs_single_timer(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 2  # one immediate send per setup
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    for _ in range(5):
        await asyncio.sleep(0)
    assert aioclient_mock.call_count == 3
