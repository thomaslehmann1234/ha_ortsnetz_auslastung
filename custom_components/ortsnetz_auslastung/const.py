DOMAIN = "ortsnetz_auslastung"
CONF_API_URL = "api_url"
CONF_L1_ENTITY = "l1_entity"
CONF_L2_ENTITY = "l2_entity"
CONF_L3_ENTITY = "l3_entity"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_PLANT_CAPACITY_KWP = "plant_capacity_kwp"
CONF_PV_FORECAST_ENTITY = "pv_forecast_entity"
CONF_SMARTMETER_MODEL = "smartmeter_model"
CONF_GRID_FREQUENCY_ENTITY = "grid_frequency_entity"
PLATFORMS = ["sensor"]
MIN_PHASE_VOLTAGE_V = 150.0
MAX_PHASE_VOLTAGE_V = 300.0
INTEGRATION_VERSION = "0.3.6"


def status_signal(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_status"
