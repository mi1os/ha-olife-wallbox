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

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    REG_CURRENT_LIMIT_A,
    REG_CURRENT_LIMIT_B,
    REG_LED_PWM,
    REG_MAX_STATION_CURRENT,
    REG_RS485_ID,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

# Error count threshold for reducing log spam
ERROR_LOG_THRESHOLD = 10

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
            # Add global number entity
            OlifeWallboxRS485ID(client, name, device_info, device_unique_id),
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
    """Number entity to control current limit on Olife Energy Wallbox (actual set current)."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:current-ac"

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
        """Return the step value."""
        return 1

    async def async_set_native_value(self, value):
        """Set the value."""
        if not self._available:
            _LOGGER.warning("Cannot set current limit: Device unavailable")
            raise HomeAssistantError("Cannot set current limit: Device unavailable")
            
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
            
            if await self._client.write_register(REG_CURRENT_LIMIT_A, scaled_value):
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
            result = await self._client.read_holding_registers(REG_CURRENT_LIMIT_A, 1)
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
                    "Error updating current limit: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxLedPwm(OlifeWallboxNumberBase):
    """Number entity to control LED PWM on Olife Energy Wallbox."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:led-outline"

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
        """Set the value."""
        if not self._available:
            _LOGGER.warning("Cannot set LED brightness: Device unavailable")
            raise HomeAssistantError("Cannot set LED brightness: Device unavailable")
            
        try:
            _LOGGER.debug("Setting LED brightness to: %s (type: %s)", value, type(value))
            # Ensure value is an integer
            scaled_value = int(round(float(value)))
            _LOGGER.debug("Converted LED brightness value to integer: %s", scaled_value)
            
            # Ensure value is within valid range
            if scaled_value < 0:
                scaled_value = 0
                _LOGGER.warning("LED brightness value below minimum, setting to 0")
            elif scaled_value > 1000:
                scaled_value = 1000
                _LOGGER.warning("LED brightness value above maximum, setting to 1000")
            
            if await self._client.write_register(REG_LED_PWM, scaled_value):
                self._value = value
                self._error_count = 0
                _LOGGER.info("LED brightness set to: %s", value)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to set LED brightness to %s (error count: %s)",
                        value, self._error_count
                    )
                raise HomeAssistantError(f"Failed to set LED brightness to {value}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error setting LED brightness to %s: %s (error count: %s)",
                    value, ex, self._error_count
                )
            raise HomeAssistantError(f"Error setting LED brightness: {ex}")

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
    """Entity to display the PP current limit (read-only, determined by the cable)."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:current-ac"

    @property
    def name(self):
        """Return the name of the entity."""
        return "Cable Current Limit"
        
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

    @property
    def read_only(self) -> bool:
        """Return True as this is a read-only entity."""
        return True
        
    async def async_set_native_value(self, value):
        """This is a read-only entity, so this method should not be called."""
        _LOGGER.warning("Cannot set PP current limit as it is read-only (determined by the cable)")
        raise HomeAssistantError("PP current limit is read-only and determined by the charging cable")

    async def async_update(self):
        """Update the state of the entity."""
        try:
            result = await self._client.read_holding_registers(REG_MAX_STATION_CURRENT, 1)
            if result is not None:
                self._available = True
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

class OlifeWallboxRS485ID(OlifeWallboxNumberBase):
    """Number entity for RS485 ID setting."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the number entity."""
        super().__init__(client, name, device_info, device_unique_id)
        # Start as unavailable until we can verify register exists
        self._available = False
        self._register_available = False
        
    @property
    def name(self):
        """Return the name of the number entity."""
        return "RS485 Modbus ID"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_rs485_id"
        
    @property
    def native_value(self):
        """Return the value reported by the number entity."""
        if not self._register_available:
            return None
        return self._value
        
    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 0
        
    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 16
        
    @property
    def native_step(self):
        """Return the step value."""
        return 1
    
    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False  # Disabled by default as this might not be supported on all models
        
    async def async_set_native_value(self, value):
        """Set the value of the entity."""
        if not self._available or not self._register_available:
            _LOGGER.warning("Cannot set RS485 ID: Device unavailable or register not supported")
            raise HomeAssistantError("Cannot set RS485 ID: Device unavailable or register not supported")
            
        try:
            _LOGGER.debug("Setting RS485 ID to: %s (type: %s)", value, type(value))
            # Ensure value is an integer
            scaled_value = int(round(float(value)))
            _LOGGER.debug("Converted RS485 ID value to integer: %s", scaled_value)
            
            # Ensure value is within valid range
            if scaled_value < 0:
                scaled_value = 0
                _LOGGER.warning("RS485 ID value below minimum, setting to 0")
            elif scaled_value > 16:
                scaled_value = 16
                _LOGGER.warning("RS485 ID value above maximum, setting to 16")
            
            if await self._client.write_register(REG_RS485_ID, scaled_value):
                self._value = value
                self._error_count = 0
                _LOGGER.info("RS485 ID set to: %s", value)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to set RS485 ID to %s (error count: %s)",
                        value, self._error_count
                    )
                raise HomeAssistantError(f"Failed to set RS485 ID to {value}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error setting RS485 ID to %s: %s (error count: %s)",
                    value, ex, self._error_count
                )
            raise HomeAssistantError(f"Error setting RS485 ID: {ex}")
            
    async def async_update(self):
        """Update the state of the entity."""
        try:
            # Check if we've already determined the register is not available
            if hasattr(self, '_register_not_supported') and self._register_not_supported:
                self._available = False
                self._register_available = False
                return
                
            result = await self._client.read_holding_registers(REG_RS485_ID, 1)
            if result is not None:
                self._available = True
                self._register_available = True
                self._value = result[0]
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read RS485 ID (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            # Check for specific Modbus exceptions that indicate register is not supported
            if "Slave Device Failure" in str(ex) or "Illegal Address" in str(ex):
                # Register not supported by this model
                if not hasattr(self, '_register_not_supported') or not self._register_not_supported:
                    _LOGGER.info("RS485 ID register (5023) not supported by this device, disabling entity")
                    self._register_not_supported = True
                self._available = False
                self._register_available = False
            elif self._should_log_error():
                _LOGGER.warning(
                    "Error updating RS485 ID: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False 