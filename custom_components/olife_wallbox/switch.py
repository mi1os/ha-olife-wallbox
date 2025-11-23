"""Switch platform for Olife Energy Wallbox integration."""
import logging
from typing import Optional, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    CONF_HOST, 
    CONF_PORT, 
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    REG_AUTOMATIC,
    REG_AUTOMATIC_DIPSWITCH_ON,
    REG_MAX_CURRENT_DIPSWITCH_ON,
    REG_BALANCING_EXTERNAL_CURRENT,
    ERROR_LOG_THRESHOLD
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox switch platform."""
    try:
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
        
        # Check if we're in read-only mode
        read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
        
        if read_only:
            _LOGGER.info("Running in read-only mode, no switch entities will be created")
            return
            
        entities = [
            # OlifeWallboxChargingAuthorizationSwitch(client, name, device_info, device_unique_id),  # Moved to button platform
            OlifeWallboxAutomaticGlobalSwitch(client, name, device_info, device_unique_id),  # Automatic mode (main control)
            OlifeWallboxAutomaticDipswitchSwitch(client, name, device_info, device_unique_id),  # Automatic mode dipswitch control
            OlifeWallboxMaxCurrentDipswitchSwitch(client, name, device_info, device_unique_id),  # Max current dipswitch control
            OlifeWallboxBalancingExternalCurrentSwitch(client, name, device_info, device_unique_id),
            OlifeWallboxSolarModeSwitch(hass, entry.entry_id, name, device_info, device_unique_id),  # Solar mode toggle
        ]
        
        async_add_entities(entities)
    except Exception as ex:
        _LOGGER.error("Error setting up Olife Wallbox switch platform: %s", ex)

class OlifeWallboxSwitchBase(SwitchEntity):
    """Base class for Olife Energy Wallbox switches."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the switch."""
        self._client = client
        self._name = name
        self._is_on = False
        self._available = False
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._attr_should_poll = True  # Switches update via async_update
        self._error_count = 0
        self._register = None  # Subclasses need to define this
        
    @property
    def available(self):
        """Return if entity is available."""
        return self._available
        
    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info
        
    @property
    def state(self) -> str:
        """Return the state of the entity."""
        if not self._available:
            return STATE_UNAVAILABLE
        return STATE_ON if self._is_on else STATE_OFF
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0
        
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if not self._available:
            _LOGGER.warning("Cannot turn on %s: Device unavailable", self.name)
            raise HomeAssistantError(f"Cannot turn on {self.name}: Device unavailable")
            
        if not self._register:
            _LOGGER.error("Register not defined for %s", self.name)
            raise HomeAssistantError(f"Register not defined for {self.name}")
            
        try:
            _LOGGER.debug("Turning on %s", self.name)
            
            if await self._client.write_register(self._register, 1):
                self._is_on = True
                self._error_count = 0
                _LOGGER.info("%s turned on", self.name)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to turn on %s (error count: %s)",
                        self.name, self._error_count
                    )
                raise HomeAssistantError(f"Failed to turn on {self.name}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error turning on %s: %s (error count: %s)",
                    self.name, ex, self._error_count
                )
            raise HomeAssistantError(f"Error turning on {self.name}: {ex}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if not self._available:
            _LOGGER.warning("Cannot turn off %s: Device unavailable", self.name)
            raise HomeAssistantError(f"Cannot turn off {self.name}: Device unavailable")
            
        if not self._register:
            _LOGGER.error("Register not defined for %s", self.name)
            raise HomeAssistantError(f"Register not defined for {self.name}")
            
        try:
            _LOGGER.debug("Turning off %s", self.name)
            
            if await self._client.write_register(self._register, 0):
                self._is_on = False
                self._error_count = 0
                _LOGGER.info("%s turned off", self.name)
                self.async_write_ha_state()
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to turn off %s (error count: %s)",
                        self.name, self._error_count
                    )
                raise HomeAssistantError(f"Failed to turn off {self.name}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error turning off %s: %s (error count: %s)",
                    self.name, ex, self._error_count
                )
            raise HomeAssistantError(f"Error turning off {self.name}: {ex}")
            
    async def async_update(self):
        """Update the state of the switch."""
        if not self._register:
            _LOGGER.error("Register not defined for %s", self.name)
            self._available = False
            return
            
        try:
            result = await self._client.read_holding_registers(self._register, 1)
            if result is not None:
                self._available = True
                self._is_on = result[0] == 1
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read %s state (error count: %s)",
                        self.name, self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error updating %s state: %s (error count: %s)",
                    self.name, ex, self._error_count
                )
            self._available = False



class OlifeWallboxAutomaticGlobalSwitch(OlifeWallboxSwitchBase):
    """Switch for Olife Energy Wallbox automatic mode setting (global register 5003)."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the switch."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:check-decagram"
        self._register = REG_AUTOMATIC
        self._attr_entity_category = EntityCategory.CONFIG  # Move to configuration tab
        # Start as unavailable until we can verify register exists
        self._available = False
        self._register_available = False
        
    @property
    def available(self):
        """Return True if entity is available."""
        if hasattr(self, '_register_not_supported') and self._register_not_supported:
            return False
        return self._available and self._register_available
        
    @property
    def name(self):
        """Return the name of the switch."""
        return "Automatic Mode"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_automatic_global_switch"
        
    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return True  # Enable by default as this is the main automatic mode control
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the switch state."""
        if not self._available:
            return "mdi:lightning-bolt-off"
        return "mdi:lightning-bolt" if self._is_on else "mdi:lightning-bolt-off"
        
    async def async_update(self):
        """Update the switch's state."""
        try:
            # Check if we've already determined the register is not available
            if hasattr(self, '_register_not_supported') and self._register_not_supported:
                self._available = False
                self._register_available = False
                return
                
            result = await self._client.read_holding_registers(self._register, 1)
            if result is not None:
                self._available = True
                self._register_available = True
                self._is_on = bool(result[0])
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read Automatic Mode Global (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            # Check for specific Modbus exceptions that indicate register is not supported
            if "Slave Device Failure" in str(ex) or "Illegal Address" in str(ex):
                # Register not supported by this model
                if not hasattr(self, '_register_not_supported') or not self._register_not_supported:
                    _LOGGER.info("Automatic Mode Global register (%s) not supported by this device, disabling entity", 
                                self._register)
                    self._register_not_supported = True
                self._available = False
                self._register_available = False
            elif self._should_log_error():
                _LOGGER.warning(
                    "Error updating Automatic Mode Global: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxAutomaticDipswitchSwitch(OlifeWallboxSwitchBase):
    """Switch for Olife Energy Wallbox automatic mode dipswitch setting."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the switch."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:dip-switch"
        self._register = REG_AUTOMATIC_DIPSWITCH_ON
        self._attr_entity_category = EntityCategory.CONFIG  # Move to configuration tab
        # Start as unavailable until we can verify register exists
        self._available = False
        self._register_available = False
        
    @property
    def available(self):
        """Return True if entity is available."""
        if hasattr(self, '_register_not_supported') and self._register_not_supported:
            return False
        return self._available and self._register_available
        
    @property
    def name(self):
        """Return the name of the switch."""
        return "Automatic Mode Dipswitch"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_auto_dipswitch"
        
    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False  # Disabled by default as this might not be supported on all models
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the switch state."""
        if not self._available:
            return "mdi:dip-switch"
        return "mdi:toggle-switch" if self._is_on else "mdi:toggle-switch-off"
        
    async def async_update(self):
        """Update the switch's state."""
        try:
            # Check if we've already determined the register is not available
            if hasattr(self, '_register_not_supported') and self._register_not_supported:
                self._available = False
                self._register_available = False
                return
                
            result = await self._client.read_holding_registers(self._register, 1)
            if result is not None:
                self._available = True
                self._register_available = True
                self._is_on = bool(result[0])
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read Automatic Mode Dipswitch (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            # Check for specific Modbus exceptions that indicate register is not supported
            if "Slave Device Failure" in str(ex) or "Illegal Address" in str(ex):
                # Register not supported by this model
                if not hasattr(self, '_register_not_supported') or not self._register_not_supported:
                    _LOGGER.info("Automatic Mode Dipswitch register (%s) not supported by this device, disabling entity", 
                                self._register)
                    self._register_not_supported = True
                self._available = False
                self._register_available = False
            elif self._should_log_error():
                _LOGGER.warning(
                    "Error updating Automatic Mode Dipswitch: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxMaxCurrentDipswitchSwitch(OlifeWallboxSwitchBase):
    """Switch for Olife Energy Wallbox max current dipswitch setting."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the switch."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:current-ac"
        self._register = REG_MAX_CURRENT_DIPSWITCH_ON
        self._attr_entity_category = EntityCategory.CONFIG  # Move to configuration tab
        # Start as unavailable until we can verify register exists
        self._available = False
        self._register_available = False
        
    @property
    def available(self):
        """Return True if entity is available."""
        if hasattr(self, '_register_not_supported') and self._register_not_supported:
            return False
        return self._available and self._register_available
        
    @property
    def name(self):
        """Return the name of the switch."""
        return "Max Current Dipswitch"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_max_current_dipswitch"
        
    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False  # Disabled by default as this might not be supported on all models
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the switch state."""
        if not self._available:
            return "mdi:current-ac"
        return "mdi:toggle-switch" if self._is_on else "mdi:toggle-switch-off"
        
    async def async_update(self):
        """Update the switch's state."""
        try:
            # Check if we've already determined the register is not available
            if hasattr(self, '_register_not_supported') and self._register_not_supported:
                self._available = False
                self._register_available = False
                return
                
            result = await self._client.read_holding_registers(self._register, 1)
            if result is not None:
                self._available = True
                self._register_available = True
                self._is_on = bool(result[0])
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read Max Current Dipswitch (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            # Check for specific Modbus exceptions that indicate register is not supported
            if "Slave Device Failure" in str(ex) or "Illegal Address" in str(ex):
                # Register not supported by this model
                if not hasattr(self, '_register_not_supported') or not self._register_not_supported:
                    _LOGGER.info("Max Current Dipswitch register (%s) not supported by this device, disabling entity", 
                                self._register)
                    self._register_not_supported = True
                self._available = False
                self._register_available = False
            elif self._should_log_error():
                _LOGGER.warning(
                    "Error updating Max Current Dipswitch: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False

class OlifeWallboxBalancingExternalCurrentSwitch(OlifeWallboxSwitchBase):
    """Switch for Olife Energy Wallbox balancing external current setting."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the switch."""
        super().__init__(client, name, device_info, device_unique_id)
        self._attr_icon = "mdi:electric-switch"
        self._register = REG_BALANCING_EXTERNAL_CURRENT
        self._attr_entity_category = EntityCategory.CONFIG  # Move to configuration tab
        # Start as unavailable until we can verify register exists
        self._available = False
        self._register_available = False
        
    @property
    def available(self):
        """Return True if entity is available."""
        if hasattr(self, '_register_not_supported') and self._register_not_supported:
            return False
        return self._available and self._register_available
        
    @property
    def name(self):
        """Return the name of the switch."""
        return "Balancing External Current"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_balancing_external_current"
        
    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False  # Disabled by default as this might not be supported on all models
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the switch state."""
        if not self._available:
            return "mdi:electric-switch"
        return "mdi:toggle-switch" if self._is_on else "mdi:toggle-switch-off"
        
    async def async_update(self):
        """Update the switch's state."""
        try:
            # Check if we've already determined the register is not available
            if hasattr(self, '_register_not_supported') and self._register_not_supported:
                self._available = False
                self._register_available = False
                return
                
            result = await self._client.read_holding_registers(self._register, 1)
            if result is not None:
                self._available = True
                self._register_available = True
                self._is_on = bool(result[0])
                self._error_count = 0
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.warning(
                        "Failed to read Balancing External Current (error count: %s)",
                        self._error_count
                    )
                self._available = False
        except Exception as ex:
            self._error_count += 1
            # Check for specific Modbus exceptions that indicate register is not supported
            if "Slave Device Failure" in str(ex) or "Illegal Address" in str(ex):
                # Register not supported by this model
                if not hasattr(self, '_register_not_supported') or not self._register_not_supported:
                    _LOGGER.info("Balancing External Current register (%s) not supported by this device, disabling entity", 
                                self._register)
                    self._register_not_supported = True
                self._available = False
                self._register_available = False
            elif self._should_log_error():
                _LOGGER.warning(
                    "Error updating Balancing External Current: %s (error count: %s)",
                    ex, self._error_count
                )
            self._available = False 

class OlifeWallboxSolarModeSwitch(SwitchEntity):
    """Switch to enable/disable solar mode."""

    def __init__(self, hass, entry_id, name, device_info, device_unique_id):
        """Initialize the solar mode switch."""
        self.hass = hass
        self._entry_id = entry_id
        self._name = name
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._attr_should_poll = False  # This is a virtual switch, no polling needed
        self._attr_icon = "mdi:solar-power"
        self._attr_entity_category = EntityCategory.CONFIG
        self._is_on = False
        
    @property
    def name(self):
        """Return the name of the switch."""
        return "Solar Mode"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_solar_mode"
        
    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:solar-power" if self._is_on else "mdi:solar-power-variant-outline"
        
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        self.async_write_ha_state()
        
        # Enable solar optimizer if it exists
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            optimizer = self.hass.data[DOMAIN][self._entry_id].get("solar_optimizer")
            if optimizer:
                await optimizer.async_enable()
                _LOGGER.info("Solar mode enabled")
            
            # Also enable automatic mode since charging is "free" with solar
            client = self.hass.data[DOMAIN][self._entry_id].get("client")
            if client:
                try:
                    from .const import REG_AUTOMATIC
                    if await client.write_register(REG_AUTOMATIC, 1):
                        _LOGGER.info("Automatic mode enabled with solar mode")
                    else:
                        _LOGGER.warning("Failed to enable automatic mode")
                except Exception as ex:
                    _LOGGER.error("Error enabling automatic mode: %s", ex)
            
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()
        
        # Disable solar optimizer if it exists
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            optimizer = self.hass.data[DOMAIN][self._entry_id].get("solar_optimizer")
            if optimizer:
                optimizer.disable()
                _LOGGER.info("Solar mode disabled")

