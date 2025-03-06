"""Number platform for Olife Energy Wallbox integration."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    REG_CURRENT_LIMIT,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox number platform."""
    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE_ID]
    
    client = OlifeWallboxModbusClient(host, port, slave_id)
    
    # Create a unique ID for the device
    device_unique_id = f"{host}_{port}_{slave_id}"
    
    # Create device info
    device_info = DeviceInfo(
        identifiers={(DOMAIN, device_unique_id)},
        name=name,
        manufacturer="Olife Energy",
        model="Wallbox",
        sw_version="1.0",  # You can update this with actual firmware version if available
    )
    
    async_add_entities([OlifeWallboxCurrentLimit(client, name, device_info, device_unique_id)])

class OlifeWallboxCurrentLimit(NumberEntity):
    """Number entity to control current limit on Olife Energy Wallbox."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        self._client = client
        self._name = name
        self._value = None
        self._available = False
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True

    @property
    def name(self):
        """Return the name of the entity."""
        return "Current Limit"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_current_limit"
        
    @property
    def native_value(self):
        """Return the current value."""
        return self._value
        
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfElectricCurrent.AMPERE
        
    @property
    def available(self):
        """Return if entity is available."""
        return self._available
        
    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 6  # Typical minimum for EV charging
        
    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 32  # Typical maximum for EV charging
        
    @property
    def native_step(self):
        """Return the step value."""
        return 1
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info

    async def async_set_native_value(self, value):
        """Set the value."""
        # Adjust the scaling factor according to your device's specifications
        scaled_value = int(value)  # No scaling needed for the actual registers
        if await self._client.write_register(REG_CURRENT_LIMIT, scaled_value):
            self._value = value
            self.async_write_ha_state()

    async def async_update(self):
        """Update the state of the entity."""
        result = await self._client.read_holding_registers(REG_CURRENT_LIMIT, 1)
        if result is not None:
            self._available = True
            # No scaling needed for the actual registers
            self._value = result[0]
        else:
            self._available = False 