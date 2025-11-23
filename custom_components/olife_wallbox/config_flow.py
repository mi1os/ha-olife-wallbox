"""Config flow for Olife Energy Wallbox integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    # Sensor groups options
    CONF_ENABLE_PHASE_SENSORS,
    CONF_ENABLE_ERROR_SENSORS,
    # Default option values
    DEFAULT_ENABLE_PHASE_SENSORS,
    DEFAULT_ENABLE_ERROR_SENSORS,

    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
)

_LOGGER = logging.getLogger(__name__)

async def validate_connection(hass: HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    slave_id = data[CONF_SLAVE_ID]

    # Initialize with minimal parameters
    client = ModbusTcpClient(host=host, port=port)
    
    # Set the slave ID directly as an attribute
    client.unit_id = slave_id
    
    try:
        if client.connect():
            # Try reading a register to verify communication
            try:
                # Try newer API pattern
                result = client.read_holding_registers(2104, count=1)
            except TypeError:
                # Try older API pattern
                result = client.read_holding_registers(2104, 1)
                
            if not result.isError():
                return {"success": True}
            else:
                return {"error": "Failed to read data from the device"}
        else:
            return {"error": "Failed to connect to the device"}
    except ConnectionException:
        return {"error": "Connection error"}
    except Exception as ex:
        return {"error": f"An error occurred: {ex}"}
    finally:
        client.close()


class OlifeWallboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Olife Energy Wallbox."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the connection
            validation_result = await validate_connection(self.hass, user_input)
            if "success" in validation_result:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
            else:
                errors["base"] = validation_result.get("error", "unknown_error")

        # Fill in default values
        if user_input is None:
            user_input = {}
        
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Olife Wallbox")): str,
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Required(CONF_SLAVE_ID, default=user_input.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OlifeWallboxOptionsFlow(config_entry)


class OlifeWallboxOptionsFlow(config_entries.OptionsFlow):
    """Handle Olife Energy Wallbox options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_READ_ONLY,
                default=self.entry.options.get(
                    CONF_READ_ONLY, DEFAULT_READ_ONLY
                ),
                description={"suggested_value": self.entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)}
            ): bool,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.entry.options.get(
                    CONF_SCAN_INTERVAL, self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            vol.Optional(
                CONF_ENABLE_PHASE_SENSORS,
                default=self.entry.options.get(
                    CONF_ENABLE_PHASE_SENSORS, DEFAULT_ENABLE_PHASE_SENSORS
                ),
            ): bool,
            vol.Optional(
                CONF_ENABLE_ERROR_SENSORS,
                default=self.entry.options.get(
                    CONF_ENABLE_ERROR_SENSORS, DEFAULT_ENABLE_ERROR_SENSORS
                ),
            ): bool,

        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options)) 