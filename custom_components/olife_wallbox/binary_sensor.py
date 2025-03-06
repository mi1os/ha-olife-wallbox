"""Binary sensor platform for Olife Energy Wallbox integration."""
import logging
from datetime import timedelta
import async_timeout

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    FAST_SCAN_INTERVAL,
    # Register addresses
    REG_VERIFY_USER,
    REG_AUTOMATIC,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox binary sensor platform."""
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
    
    async def async_update_data():
        """Fetch data from the wallbox."""
        async with async_timeout.timeout(10):
            data = {}
            
            # Read verify user status
            verify_user = await client.read_holding_registers(REG_VERIFY_USER, 1)
            if verify_user is not None:
                data["verify_user"] = verify_user[0] == 1
                
            # Read automatic mode status
            automatic = await client.read_holding_registers(REG_AUTOMATIC, 1)
            if automatic is not None:
                data["automatic"] = automatic[0] == 1
                
            return data
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="olife_wallbox_binary_sensors",
        update_method=async_update_data,
        update_interval=timedelta(seconds=FAST_SCAN_INTERVAL),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    entities = [
        OlifeWallboxVerifyUserBinarySensor(coordinator, name, "verify_user", device_info, device_unique_id),
        OlifeWallboxAutomaticBinarySensor(coordinator, name, "automatic", device_info, device_unique_id),
    ]
    
    async_add_entities(entities)

class OlifeWallboxBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Olife Energy Wallbox binary sensors."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._key in self.coordinator.data

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_{self._key}"
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info

class OlifeWallboxVerifyUserBinarySensor(OlifeWallboxBinarySensor):
    """Binary sensor for Olife Energy Wallbox user verification."""

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "Verify User"

    @property
    def is_on(self):
        """Return the state of the binary sensor."""
        return self.coordinator.data.get(self._key, False)
        
    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return BinarySensorDeviceClass.POWER

class OlifeWallboxAutomaticBinarySensor(OlifeWallboxBinarySensor):
    """Binary sensor for Olife Energy Wallbox automatic mode."""

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return "Automatic Mode"

    @property
    def is_on(self):
        """Return the state of the binary sensor."""
        return self.coordinator.data.get(self._key, False)
        
    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return BinarySensorDeviceClass.POWER 