"""Tests for rounding the transmitted coordinates."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ortsnetz_auslastung import _send
from custom_components.ortsnetz_auslastung.const import DOMAIN

URL = "https://example.test/v1/measurements"


@pytest.mark.parametrize(
    ("latitude", "longitude", "expected"),
    [
        (52.520008, 13.404954, (52.52, 13.405)),
        (48.1374449, 11.5754931, (48.137, 11.575)),
        (-33.8688197, 151.2092955, (-33.869, 151.209)),
        (51.0, 7.0, (51.0, 7.0)),
    ],
)
async def test_coordinates_are_rounded(hass, aioclient_mock, latitude, longitude, expected):
    for entity_id in ("sensor.l1", "sensor.l2", "sensor.l3"):
        hass.states.async_set(entity_id, "230")
    aioclient_mock.post(URL, json={})
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={
        "api_url": URL, "l1_entity": "sensor.l1", "l2_entity": "sensor.l2", "l3_entity": "sensor.l3",
        "latitude": latitude, "longitude": longitude,
    })
    entry.add_to_hass(hass)

    await _send(hass, entry)

    payload = aioclient_mock.mock_calls[0][2]
    assert (payload["latitude"], payload["longitude"]) == expected
