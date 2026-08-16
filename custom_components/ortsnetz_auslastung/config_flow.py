from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import CONF_API_URL, CONF_GRID_FREQUENCY_ENTITY, CONF_L1_ENTITY, CONF_L2_ENTITY, CONF_L3_ENTITY, CONF_LATITUDE, CONF_LONGITUDE, CONF_PLANT_CAPACITY_KWP, CONF_PV_FORECAST_ENTITY, CONF_TOKEN, DOMAIN


class OrtsnetzConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Ortsnetz-Auslastung", data=user_input)

        entity_selector = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        schema = vol.Schema({
            vol.Required(CONF_API_URL, default="https://auslastung-ortsnetz.blumen38.dedyn.io"): str,
            vol.Required(CONF_TOKEN): str,
            vol.Required(CONF_L1_ENTITY): entity_selector,
            vol.Required(CONF_L2_ENTITY): entity_selector,
            vol.Required(CONF_L3_ENTITY): entity_selector,
            vol.Required(CONF_PLANT_CAPACITY_KWP): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1000)),
            vol.Required(CONF_PV_FORECAST_ENTITY): entity_selector,
            vol.Required(CONF_GRID_FREQUENCY_ENTITY): entity_selector,
            vol.Optional(CONF_LATITUDE, default=self.hass.config.latitude): vol.Coerce(float),
            vol.Optional(CONF_LONGITUDE, default=self.hass.config.longitude): vol.Coerce(float),
        })
        return self.async_show_form(step_id="user", data_schema=schema)
