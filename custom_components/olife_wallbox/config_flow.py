"""Config flow for Olife Energy Wallbox integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

async def validate_connection(hass: HomeAssistant, data):
    """Validate the connection to the Olife Energy Wallbox."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    slave_id = data[CONF_SLAVE_ID]
    
    client = ModbusTcpClient(host=host, port=port)
    client.unit_id = slave_id  # Set the unit_id/slave_id before making the request
    
    try:
        await hass.async_add_executor_job(client.connect)
        # Try to read a register to verify connection
        # Use a lambda to wrap the call to handle different pymodbus versions
        result = await hass.async_add_executor_job(
            lambda: client.read_holding_registers(address=1000, count=1)
        )
        await hass.async_add_executor_job(client.close)
        
        if hasattr(result, 'isError') and result.isError():
            return False
        return True
    except ConnectionException:
        return False
    except Exception as ex:
        _LOGGER.error("Error connecting to Olife Wallbox: %s", ex)
        return False
    finally:
        if client.connected:
            await hass.async_add_executor_job(client.close)

class OlifeWallboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Olife Energy Wallbox."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the connection
            is_valid = await validate_connection(self.hass, user_input)
            
            if is_valid:
                # Create entry
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        # Show the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Olife Wallbox"): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        ) 