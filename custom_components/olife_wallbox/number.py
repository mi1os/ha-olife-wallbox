"""Number platform for Olife Energy Wallbox integration."""
import logging
from typing import Optional

from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    CONF_HOST, 
    CONF_PORT, 
    CONF_NAME, 
    UnitOfElectricCurrent,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    REG_CURRENT_LIMIT_A,
    REG_CURRENT_LIMIT_B,
    REG_CLOUD_CURRENT_LIMIT_A,
    REG_CLOUD_CURRENT_LIMIT_B,
    REG_LED_PWM,
    REG_MAX_STATION_CURRENT,
    CONF_SCAN_INTERVAL,
    ERROR_LOG_THRESHOLD
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
            sw_version="1.0",  # You can update this with actual firmware version if available
        )
        
        read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
        
        entities = [
            OlifeWallboxCurrentLimit(client, name, device_info, device_unique_id),
            OlifeWallboxLedPwm(client, name, device_info, device_unique_id),
            OlifeWallboxMaxStationCurrent(client, name, device_info, device_unique_id),
        ]
        
        async_add_entities(entities)
    except Exception as ex:
        _LOGGER.error("Error setting up Olife Wallbox number platform: %s", ex)

class OlifeWallboxNumberBase(NumberEntity):
    """Base class for Olife Energy Wallbox number entities."""
    
    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        self._client = client
        self._name = name
        self._value = None
        self._available = False
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._error_count = 0
        
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
        if self._value is None:
            return STATE_UNKNOWN
        return self._value
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0

class OlifeWallboxCurrentLimit(OlifeWallboxNumberBase):
    """Number entity to control current limit on Olife Energy Wallbox."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:current-ac"
        self._attr_entity_category = EntityCategory.CONFIG  # Move to configuration tab

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
    def native_min_value(self):
        """Return the minimum value."""
        return 0  # Allow turning off completely
        
    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 32  # Maximum for EV charging
        
    @property
    def native_step(self):
        """Return the step size."""
        return 1  # 1 Amp steps

    async def async_set_native_value(self, value):
        """Set the value."""
        try:
            _LOGGER.debug("Setting current limit to: %s (type: %s)", value, type(value))
            # Ensure value is an integer
            scaled_value = int(round(float(value)))
            _LOGGER.debug("Converted current limit value to integer: %s", scaled_value)
            
            # Ensure value is within valid range
            if scaled_value < 6:
                scaled_value = 6
                _LOGGER.warning("Current limit value below minimum, setting to 6")
            elif scaled_value > 32:
                scaled_value = 32
                _LOGGER.warning("Current limit value above maximum, setting to 32")
            
            # Determine which register to use based on connector
            # For most implementations, we use connector B registers
            # REG_CURRENT_LIMIT_A (2007) and REG_CURRENT_LIMIT_B (2107) are read-only
            # We should use REG_CLOUD_CURRENT_LIMIT_A (2006) or REG_CLOUD_CURRENT_LIMIT_B (2106)
            if await self._client.write_register(REG_CLOUD_CURRENT_LIMIT_B, scaled_value):
                self._value = value
                self._error_count = 0
                _LOGGER.info("Current limit set to: %s", value)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to set current limit to %s (error count: %s)",
                        value, self._error_count
                    )
                raise HomeAssistantError(f"Failed to set current limit to {value}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error setting current limit to %s: %s (error count: %s)",
                    value, ex, self._error_count
                )
            raise HomeAssistantError(f"Error setting current limit: {ex}")

    async def async_update(self):
        """Update the state of the entity."""
        try:
            # Read the current limit value
            # Use REG_CURRENT_LIMIT_B for reading as it contains the actual current limit
            result = await self._client.read_holding_registers(REG_CURRENT_LIMIT_B, 1)
            if result is not None:
                self._available = True
                self._value = result[0]
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read current limit (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error reading current limit: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxLedPwm(OlifeWallboxNumberBase):
    """Entity for controlling the LED PWM value."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:led-on"
        self._attr_entity_category = EntityCategory.CONFIG
        # Add optimistic mode
        self._attr_assumed_state = True

    @property
    def name(self):
        """Return the name of the entity."""
        return "LED Brightness"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_led_pwm"
        
    @property
    def native_value(self):
        """Return the current value."""
        return self._value
        
    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 0
        
    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 1000
        
    @property
    def native_step(self):
        """Return the step value."""
        return 25

    async def async_set_native_value(self, value):
        """Set the LED PWM value."""
        try:
            # Set the value optimistically before sending to device
            old_value = self._value
            self._value = value
            self.async_write_ha_state()
            
            _LOGGER.debug("Setting LED PWM to %s", value)
            
            # Write the value to the register
            result = await self._client.write_register(REG_LED_PWM, int(value))
            if not result:
                # Revert to old value if failed
                _LOGGER.error("Failed to set LED PWM")
                self._value = old_value
                self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.error("Error setting LED PWM: %s", ex)
            # Revert optimistic update on error
            self._value = old_value
            self.async_write_ha_state()
            raise HomeAssistantError(f"Error setting LED PWM: {ex}") from ex

    async def async_update(self):
        """Update the state of the entity."""
        try:
            result = await self._client.read_holding_registers(REG_LED_PWM, 1)
            if result is not None:
                self._available = True
                self._value = result[0]
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read LED brightness (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error updating LED brightness: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxMaxStationCurrent(OlifeWallboxNumberBase):
    """Entity to display and set the max station current."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:current-ac"
        self._attr_entity_category = EntityCategory.CONFIG
        # Add optimistic mode
        self._attr_assumed_state = True

    @property
    def name(self):
        """Return the name of the entity."""
        return "Max Station Current"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_max_station_current"
        
    @property
    def native_value(self):
        """Return the current value."""
        return self._value
        
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfElectricCurrent.AMPERE
        
    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 0
        
    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 63
        
    @property
    def native_step(self):
        """Return the step value."""
        return 1

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled by default."""
        return True
        
    async def async_set_native_value(self, value):
        """Set the max station current value."""
        try:
            # Set the value optimistically before sending to device
            old_value = self._value
            self._value = value
            self.async_write_ha_state()
            
            # Register 5006 values are in amps
            amp_value = int(value)
            
            _LOGGER.debug(
                "Setting max station current to %s A",
                amp_value
            )
            
            # Write the value to the register
            result = await self._client.write_register(REG_MAX_STATION_CURRENT, amp_value)
            if not result:
                # Revert to old value if failed
                _LOGGER.error("Failed to set max station current")
                self._value = old_value
                self.async_write_ha_state()
        except Exception as ex:
            _LOGGER.error("Error setting max station current: %s", ex)
            # Revert optimistic update on error
            self._value = old_value
            self.async_write_ha_state()
            raise HomeAssistantError(f"Error setting max station current: {ex}") from ex

    async def async_update(self):
        """Update the state of the entity."""
        try:
            # Reading register 5006 (REG_MAX_STATION_CURRENT)
            result = await self._client.read_holding_registers(REG_MAX_STATION_CURRENT, 1)
            if result is not None:
                self._available = True
                # The value is in amps, no conversion needed
                self._value = result[0]
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read max station current (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error updating max station current: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False 