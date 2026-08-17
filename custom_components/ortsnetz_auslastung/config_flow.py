from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import CONF_API_URL, CONF_GRID_FREQUENCY_ENTITY, CONF_L1_ENTITY, CONF_L2_ENTITY, CONF_L3_ENTITY, CONF_LATITUDE, CONF_LONGITUDE, CONF_PLANT_CAPACITY_KWP, CONF_PV_FORECAST_ENTITY, DOMAIN

PHASE_VOLTAGES_SECTION = "phase_voltages"


def _required_field(key: str, validator, values: dict, fallback=None):
    """Preserve saved values as form defaults without inventing empty ones."""
    if key in values or fallback is not None:
        return vol.Required(key, default=values.get(key, fallback)), validator
    return vol.Required(key), validator


def _optional_field(key: str, validator, values: dict):
    """Show an optional field only with a default when a value was saved."""
    if values.get(key):
        return vol.Optional(key, default=values[key]), validator
    return vol.Optional(key), validator


def _settings_schema(hass, values: dict) -> vol.Schema:
    """Build setup and options fields for the token-free measurement API."""
    entity_selector = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
    phase_fields = dict([
        _required_field(CONF_L1_ENTITY, entity_selector, values),
        _required_field(CONF_L2_ENTITY, entity_selector, values),
        _required_field(CONF_L3_ENTITY, entity_selector, values),
    ])
    fields = dict([
        _required_field(CONF_API_URL, str, values, "https://www.ortsnetz-auslastung.de"),
        (vol.Required(PHASE_VOLTAGES_SECTION), section(vol.Schema(phase_fields), {"collapsed": False})),
        _required_field(CONF_GRID_FREQUENCY_ENTITY, entity_selector, values),
        _required_field(CONF_PLANT_CAPACITY_KWP, vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1000)), values),
        _optional_field(CONF_PV_FORECAST_ENTITY, entity_selector, values),
        (vol.Optional(CONF_LATITUDE, default=values.get(CONF_LATITUDE, hass.config.latitude)), vol.Coerce(float)),
        (vol.Optional(CONF_LONGITUDE, default=values.get(CONF_LONGITUDE, hass.config.longitude)), vol.Coerce(float)),
    ])
    return vol.Schema(fields)


def _flatten_sections(user_input: dict) -> dict:
    """Keep the stored config flat although the form groups phase inputs."""
    data = dict(user_input)
    data.update(data.pop(PHASE_VOLTAGES_SECTION, {}))
    return data


class OrtsnetzConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Ortsnetz-Auslastung", data=_flatten_sections(user_input))

        return self.async_show_form(step_id="user", data_schema=_settings_schema(self.hass, {}))

    @staticmethod
    def async_get_options_flow(config_entry):
        return OrtsnetzOptionsFlow()


class OrtsnetzOptionsFlow(config_entries.OptionsFlow):
    """Edit non-secret settings after setup."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=_flatten_sections(user_input))

        values = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(self.hass, values),
        )
