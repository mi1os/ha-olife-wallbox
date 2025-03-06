"""Sensor platform for Olife Energy Wallbox integration."""
import logging
from datetime import timedelta
import async_timeout

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    UnitOfElectricCurrent,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    REG_CHARGING_CURRENT,
    REG_ENERGY_TOTAL,
    REG_CHARGING_STATUS,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox sensor platform."""
    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE_ID]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    
    client = OlifeWallboxModbusClient(host, port, slave_id)
    
    async def async_update_data():
        """Fetch data from the wallbox."""
        async with async_timeout.timeout(10):
            data = {}
            
            # Read charging current
            current = await client.read_holding_registers(REG_CHARGING_CURRENT, 1)
            if current:
                # Adjust the scaling factor according to your device's specifications
                data["charging_current"] = current[0] / 10.0
                
            # Read total energy
            energy = await client.read_holding_registers(REG_ENERGY_TOTAL, 2)
            if energy:
                # Combine two registers into a 32-bit value and adjust scaling
                data["energy_total"] = (energy[0] << 16 | energy[1]) / 1000.0
                
            # Read charging status
            status = await client.read_holding_registers(REG_CHARGING_STATUS, 1)
            if status:
                data["charging_status"] = status[0]
                
            return data
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="olife_wallbox",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    entities = [
        OlifeWallboxCurrentSensor(coordinator, name, "charging_current"),
        OlifeWallboxEnergySensor(coordinator, name, "energy_total"),
        OlifeWallboxStatusSensor(coordinator, name, "charging_status"),
    ]
    
    async_add_entities(entities)

class OlifeWallboxSensor(CoordinatorEntity, SensorEntity):
    """Base class for Olife Energy Wallbox sensors."""

    def __init__(self, coordinator, name, key):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._name = name
        
    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._key in self.coordinator.data
        
    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._name}_{self._key}"

class OlifeWallboxCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charging current."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Charging Current"
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)
        
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfElectricCurrent.AMPERE
        
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.CURRENT
        
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT

class OlifeWallboxEnergySensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox total energy."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Total Energy"
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)
        
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR
        
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.ENERGY
        
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

class OlifeWallboxStatusSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charging status."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Status"
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        status_code = self.coordinator.data.get(self._key)
        if status_code is None:
            return None
            
        # Map status codes to human-readable values
        # Adjust these mappings according to your device's specifications
        status_map = {
            0: "Idle",
            1: "Connected",
            2: "Charging",
            3: "Error",
            4: "Unavailable",
        }
        return status_map.get(status_code, f"Unknown ({status_code})") 