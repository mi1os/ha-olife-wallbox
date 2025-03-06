"""Select platform for Olife Energy Wallbox integration."""
import logging
from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    REG_CHARGING_MODE,
    CHARGING_MODES,
    CHARGING_MODE_VALUES,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox select platform."""
    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE_ID]
    
    try:
        client = OlifeWallboxModbusClient(host, port, slave_id)
        
        # Create a unique ID for the device
        device_unique_id = f"{host}_{port}_{slave_id}"
        
        # Create device info
        device_info = DeviceInfo(
            identifiers={(DOMAIN, device_unique_id)},
            name=name,
            manufacturer="Olife Energy",
            model="Wallbox",
            sw_version="1.0",
        )
        
        async_add_entities([OlifeWallboxChargingModeSelect(client, name, device_info, device_unique_id)])
    except Exception as ex:
        _LOGGER.error("Error setting up Olife Wallbox select platform: %s", ex)

class OlifeWallboxChargingModeSelect(SelectEntity):
    """Select entity for Olife Energy Wallbox charging mode."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the select entity."""
        self._client = client
        self._name = name
        self._current_option = None
        self._available = False
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:ev-station"
        self._attr_options = CHARGING_MODES
        self._error_count = 0
        self._state = STATE_UNKNOWN

    @property
    def name(self):
        """Return the name of the entity."""
        return "Charging Mode"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_charging_mode"
        
    @property
    def current_option(self):
        """Return the current selected option."""
        return self._current_option
        
    @property
    def available(self):
        """Return if entity is available."""
        return self._available
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info
        
    @property
    def state(self):
        """Return the state of the entity."""
        if not self._available:
            return STATE_UNAVAILABLE
        if self._current_option is None:
            return STATE_UNKNOWN
        return self._current_option
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the charging mode."""
        if not self._available or self._current_option is None:
            return "mdi:ev-station-off"
            
        icons = {
            "fast": "mdi:ev-station",
            "solar": "mdi:solar-power-variant",
            "spot": "mdi:flash",
            "off": "mdi:ev-station-off"
        }
        
        return icons.get(self._current_option, "mdi:ev-station")

    async def async_select_option(self, option):
        """Change the selected option."""
        if not self._available:
            _LOGGER.warning("Cannot set charging mode: Device unavailable")
            raise HomeAssistantError("Cannot set charging mode: Device unavailable")
            
        if option not in CHARGING_MODE_VALUES:
            _LOGGER.error("Invalid charging mode: %s", option)
            raise HomeAssistantError(f"Invalid charging mode: {option}")
            
        try:
            _LOGGER.debug("Setting charging mode to: %s", option)
            value = CHARGING_MODE_VALUES[option]
            
            if await self._client.write_register(REG_CHARGING_MODE, value):
                self._current_option = option
                self._error_count = 0
                _LOGGER.info("Charging mode set to: %s", option)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                _LOGGER.error(
                    "Failed to set charging mode to %s (error count: %s)",
                    option, self._error_count
                )
                raise HomeAssistantError(f"Failed to set charging mode to {option}")
        except Exception as ex:
            self._error_count += 1
            _LOGGER.error(
                "Error setting charging mode to %s: %s (error count: %s)",
                option, ex, self._error_count
            )
            raise HomeAssistantError(f"Error setting charging mode: {ex}")

    async def async_update(self):
        """Update the state of the entity."""
        try:
            result = await self._client.read_holding_registers(REG_CHARGING_MODE, 1)
            
            if result is not None:
                self._available = True
                value = result[0]
                
                # Find the mode name for this value
                mode_found = False
                for mode, mode_value in CHARGING_MODE_VALUES.items():
                    if mode_value == value:
                        if self._current_option != mode:
                            _LOGGER.info("Charging mode changed to: %s", mode)
                        self._current_option = mode
                        mode_found = True
                        break
                        
                if not mode_found:
                    _LOGGER.warning(
                        "Unknown charging mode value received: %s, defaulting to %s",
                        value, CHARGING_MODES[0]
                    )
                    self._current_option = CHARGING_MODES[0]
                    
                # Reset error count on successful update
                self._error_count = 0
            else:
                self._error_count += 1
                if self._error_count == 1 or self._error_count % 10 == 0:  # Log on first error and every 10th error
                    _LOGGER.warning(
                        "Failed to read charging mode (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            if self._error_count == 1 or self._error_count % 10 == 0:  # Log on first error and every 10th error
                _LOGGER.error(
                    "Error updating charging mode: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False 