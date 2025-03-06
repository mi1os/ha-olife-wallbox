"""Switch platform for Olife Energy Wallbox integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    REG_CHARGING_ENABLE,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox switch platform."""
    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE_ID]
    
    client = OlifeWallboxModbusClient(host, port, slave_id)
    
    async_add_entities([OlifeWallboxChargingSwitch(client, name)])

class OlifeWallboxChargingSwitch(SwitchEntity):
    """Switch to control charging on Olife Energy Wallbox."""

    def __init__(self, client, name):
        """Initialize the switch."""
        self._client = client
        self._name = name
        self._is_on = False
        self._available = False

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{self._name} Charging"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._name}_charging_switch"
        
    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on
        
    @property
    def available(self):
        """Return if entity is available."""
        return self._available

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if await self._client.write_register(REG_CHARGING_ENABLE, 1):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        if await self._client.write_register(REG_CHARGING_ENABLE, 0):
            self._is_on = False
            self.async_write_ha_state()

    async def async_update(self):
        """Update the state of the switch."""
        result = await self._client.read_holding_registers(REG_CHARGING_ENABLE, 1)
        if result is not None:
            self._available = True
            self._is_on = result[0] == 1
        else:
            self._available = False 