"""Tests for the status sensors after successful and failed transmissions."""

from datetime import timedelta
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import CoreState
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

from custom_components.ortsnetz_auslastung.const import DOMAIN

URL = "https://example.test/v1/measurements"
STATUS = "sensor.netzspannungsstatus"
RECOMMENDATION = "sensor.batteriespeicherempfehlung"
GOOD = {
    "status": {"l1": "green", "l2": "yellow", "l3": "green", "overall": "yellow"},
    "storage_recommendation": "charge",
}


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("custom_components.ortsnetz_auslastung.asyncio.sleep"):
        yield


async def _setup(hass, aioclient_mock, *, language="de", legacy_ids=False, **response):
    hass.state = CoreState.running
    hass.config.language = language
    for entity_id, value in (("sensor.l1", "230"), ("sensor.l2", "231"), ("sensor.l3", "229")):
        hass.states.async_set(entity_id, value)
    aioclient_mock.post(URL, **response)
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={
        "api_url": URL, "l1_entity": "sensor.l1", "l2_entity": "sensor.l2", "l3_entity": "sensor.l3",
        "latitude": 52.5, "longitude": 13.4,
    })
    entry.add_to_hass(hass)
    if legacy_ids:
        registry = er.async_get(hass)
        for suffix, object_id in (("voltage_status", "netzspannungsstatus"), ("storage_recommendation", "batteriespeicherempfehlung")):
            registry.async_get_or_create(
                "sensor", DOMAIN, f"{entry.entry_id}_{suffix}",
                suggested_object_id=object_id, config_entry=entry,
            )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _next_cycle(hass, aioclient_mock, **response):
    aioclient_mock.clear_requests()
    aioclient_mock.post(URL, **response)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()


async def test_valid_response_sets_values(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(STATUS).attributes["L2"] == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"


@pytest.mark.parametrize("measured_phases", [(1,), (2,), (3,), (1, 2), (1, 3), (2, 3)])
async def test_excluded_phase_status_and_recovery(hass, aioclient_mock, measured_phases):
    await _setup(hass, aioclient_mock, json=GOOD)
    status = {"overall": "yellow"}
    for phase in (1, 2, 3):
        measured = phase in measured_phases
        hass.states.async_set(f"sensor.l{phase}", "243" if measured else "-1", {"unit_of_measurement": "V"})
        status[f"l{phase}"] = "yellow" if measured else "unavailable"

    await _next_cycle(hass, aioclient_mock, json={"status": status, "storage_recommendation": "charge"})

    assert aioclient_mock.call_count == 1
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"
    for phase in (1, 2, 3):
        assert hass.states.get(STATUS).attributes[f"L{phase}"] == (
            "warning" if phase in measured_phases else "unavailable"
        )

    for phase in (1, 2, 3):
        hass.states.async_set(f"sensor.l{phase}", "-1")
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert aioclient_mock.call_count == 0
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    assert hass.states.get(RECOMMENDATION).state == STATE_UNAVAILABLE

    for phase in (1, 2, 3):
        hass.states.async_set(f"sensor.l{phase}", "230")
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"


@pytest.mark.parametrize(("language", "voltage_name", "storage_name"), [
    ("de", "Netzspannungsstatus", "Batteriespeicherempfehlung"),
    ("en", "Grid voltage status", "Battery storage recommendation"),
])
async def test_sensor_names_are_translated(hass, aioclient_mock, language, voltage_name, storage_name):
    entry = await _setup(hass, aioclient_mock, language=language, json=GOOD)
    registry = er.async_get(hass)
    for suffix, expected in (("voltage_status", voltage_name), ("storage_recommendation", storage_name)):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{suffix}")
        assert hass.states.get(entity_id).name == expected


@pytest.mark.parametrize(("language", "voltage_labels", "storage_labels"), [
    ("de", ["Normal", "Warnung", "Kritisch"], ["Laden", "Entladen", "Keine Aktion"]),
    ("en", ["Normal", "Warning", "Critical"], ["Charge", "Discharge", "No action"]),
])
async def test_all_enum_states_have_translations(hass, aioclient_mock, language, voltage_labels, storage_labels):
    await _setup(hass, aioclient_mock, language=language, json=GOOD)
    translations = await async_get_translations(hass, language, "entity", {DOMAIN})
    prefix = f"component.{DOMAIN}.entity.sensor"
    for key, states, labels in (
        ("voltage_status", ["normal", "warning", "critical"], voltage_labels),
        ("storage_recommendation", ["charge", "discharge", "none"], storage_labels),
    ):
        for state, label in zip(states, labels, strict=True):
            assert translations[f"{prefix}.{key}.state.{state}"] == label


@pytest.mark.parametrize(("voltage", "expected_state", "recommendation"), [
    ("green", "normal", "none"), ("yellow", "warning", "charge"), ("red", "critical", "discharge"),
])
async def test_enum_states_and_options(hass, aioclient_mock, voltage, expected_state, recommendation):
    response = {
        "status": dict.fromkeys(("l1", "l2", "l3", "overall"), voltage),
        "storage_recommendation": recommendation,
    }
    await _setup(hass, aioclient_mock, json=response)
    status = hass.states.get(STATUS)
    storage = hass.states.get(RECOMMENDATION)
    assert status.state == expected_state
    assert storage.state == recommendation
    assert status.attributes["device_class"] == "enum"
    assert storage.attributes["device_class"] == "enum"
    assert status.attributes["options"] == ["normal", "warning", "critical"]
    assert storage.attributes["options"] == ["charge", "discharge", "none"]
    assert {key: status.attributes[key] for key in ("L1", "L2", "L3")} == dict.fromkeys(("L1", "L2", "L3"), expected_state)


async def test_existing_entity_ids_and_custom_names_survive(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock, language="en", legacy_ids=True, json=GOOD)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_voltage_status") == STATUS
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_storage_recommendation") == RECOMMENDATION
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"
    registry.async_update_entity(STATUS, name="My grid status")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_voltage_status") == STATUS
    assert hass.states.get(STATUS).name == "My grid status"


@pytest.mark.parametrize("response", [
    {"status": 500},
    {"status": 403},
    {"exc": aiohttp.ClientConnectionError()},
    {"exc": aiohttp.ServerDisconnectedError()},
    {"text": "<html>kein json</html>"},
    {"json": ["unerwartet"]},
    {"json": {"status": {"l1": [], "l2": "green", "l3": "green", "overall": "green"}, "storage_recommendation": {}}},
])
async def test_failure_marks_previous_values_unavailable(hass, aioclient_mock, response):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, **response)
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    assert hass.states.get(RECOMMENDATION).state == STATE_UNAVAILABLE


async def test_missing_voltage_sensor_marks_unavailable_without_post(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    hass.states.async_set("sensor.l2", "unavailable")
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert aioclient_mock.call_count == 0
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    assert hass.states.get(RECOMMENDATION).state == STATE_UNAVAILABLE


async def test_values_return_after_recovery(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, status=500)
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"


async def test_invalid_recommendation_only_affects_that_sensor(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, json={**GOOD, "storage_recommendation": "bogus"})
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == STATE_UNAVAILABLE


async def test_http_error_retries_once(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, status=500)
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(("status", "message"), [
    (403, "Standort gesperrt (HTTP 403)"),
    (422, "Messung abgelehnt (HTTP 422)"),
])
async def test_permanent_rejection_is_not_retried(hass, aioclient_mock, caplog, status, message):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, status=status)
    assert aioclient_mock.call_count == 1
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    assert hass.states.get(RECOMMENDATION).state == STATE_UNAVAILABLE
    assert message in caplog.text


@pytest.mark.parametrize("status", [403, 422])
async def test_regular_upload_recovers_after_permanent_rejection(hass, aioclient_mock, status):
    await _setup(hass, aioclient_mock, status=status)
    assert aioclient_mock.call_count == 1
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert aioclient_mock.call_count == 1
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"


async def test_invalid_json_is_not_resent(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, text="kein json")
    assert aioclient_mock.call_count == 1


async def test_implausible_voltage_skips_post(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    hass.states.async_set("sensor.l1", "23000")
    await _next_cycle(hass, aioclient_mock, json=GOOD)
    assert aioclient_mock.call_count == 0
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE


async def test_success_on_retry_keeps_values(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    responses = iter([aiohttp.ClientConnectionError(), None])

    async def side_effect(method, url, data):
        error = next(responses)
        if error:
            raise error
        return AiohttpClientMockResponse(method, url, json=GOOD)

    await _next_cycle(hass, aioclient_mock, side_effect=side_effect)
    assert aioclient_mock.call_count == 2
    assert hass.states.get(STATUS).state == "warning"
    assert hass.states.get(RECOMMENDATION).state == "charge"


async def test_invalid_status_only_affects_that_sensor(hass, aioclient_mock):
    await _setup(hass, aioclient_mock, json=GOOD)
    await _next_cycle(hass, aioclient_mock, json={**GOOD, "status": {"overall": "green"}})
    assert hass.states.get(STATUS).state == STATE_UNAVAILABLE
    assert hass.states.get(RECOMMENDATION).state == "charge"
