"""Button platform for Olife Energy Wallbox integration."""
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import (
    CONF_HOST, 
    CONF_PORT, 
    CONF_NAME,
    STATE_UNAVAILABLE
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
    REG_CHARGING_ENABLE_A,
    REG_CHARGING_ENABLE_B,
    ERROR_LOG_THRESHOLD
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox button platform."""
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
            sw_version="1.0",
        )
        
        # Check if we're in read-only mode
        read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
        
        if read_only:
            _LOGGER.info("Running in read-only mode, no button entities will be created")
            return
            
        entities = [
            OlifeWallboxChargingAuthorizationButton(client, name, device_info, device_unique_id),
        ]
        
        async_add_entities(entities)
    except Exception as ex:
        _LOGGER.error("Error setting up Olife Wallbox button platform: %s", ex)

class OlifeWallboxButtonBase(ButtonEntity):
    """Base class for Olife Energy Wallbox buttons."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the button."""
        self._client = client
        self._name = name
        self._available = True  # Default to true, will be updated if read fails
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._attr_should_poll = False  # Buttons don't need polling
        self._error_count = 0
        self._register = None  # Subclasses need to define this
        
    @property
    def available(self):
        """Return if entity is available."""
        return self._available
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0
            
    async def async_press(self) -> None:
        """Press the button."""
        if not self._register:
            _LOGGER.error("Register not defined for %s", self.name)
            raise HomeAssistantError(f"Register not defined for {self.name}")
            
        try:
            _LOGGER.debug("Pressing %s", self.name)
            
            # Write 1 to the register to authorize/trigger
            if await self._client.write_register(self._register, 1):
                self._error_count = 0
                _LOGGER.info("%s pressed", self.name)
            else:
                self._error_count += 1
                if self._should_log_error():
                    _LOGGER.error(
                        "Failed to press %s (error count: %s)",
                        self.name, self._error_count
                    )
                raise HomeAssistantError(f"Failed to press {self.name}")
        except Exception as ex:
            self._error_count += 1
            if self._should_log_error():
                _LOGGER.error(
                    "Error pressing %s: %s (error count: %s)",
                    self.name, ex, self._error_count
                )
            raise HomeAssistantError(f"Error pressing {self.name}: {ex}")

class OlifeWallboxChargingAuthorizationButton(OlifeWallboxButtonBase):
    """Button to authorize charging on Olife Energy Wallbox."""

    def __init__(self, client, name, device_info, device_unique_id):
        """Initialize the button."""
        super().__init__(client, name, device_info, device_unique_id)
        # For single-connector devices, always use B register
        # TODO: Accept connector parameter explicitly for dual-connector support
        self._register = REG_CHARGING_ENABLE_B
        self._attr_entity_category = None  # Main control
        
    @property
    def name(self):
        """Return the name of the button."""
        return "Charging Authorization"
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_charging_auth_button"
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:account-check"
