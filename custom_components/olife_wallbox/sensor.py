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
    UnitOfPower,
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
    REG_WALLBOX_EV_STATE,
    REG_CURRENT_LIMIT,
    REG_MAX_STATION_CURRENT,
    REG_LED_PWM,
    REG_CHARGE_CURRENT,
    REG_CHARGE_ENERGY,
    REG_CHARGE_POWER,
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
            
            # Read wallbox EV state
            ev_state = await client.read_holding_registers(REG_WALLBOX_EV_STATE, 1)
            if ev_state:
                data["wallbox_ev_state"] = ev_state[0]
                
            # Read current limit
            current_limit = await client.read_holding_registers(REG_CURRENT_LIMIT, 1)
            if current_limit:
                data["current_limit"] = current_limit[0]
                
            # Read max station current
            max_current = await client.read_holding_registers(REG_MAX_STATION_CURRENT, 1)
            if max_current:
                data["max_station_current"] = max_current[0]
                
            # Read LED PWM
            led_pwm = await client.read_holding_registers(REG_LED_PWM, 1)
            if led_pwm:
                data["led_pwm"] = led_pwm[0]
                
            # Read charge current
            charge_current = await client.read_holding_registers(REG_CHARGE_CURRENT, 1)
            if charge_current:
                data["charge_current"] = charge_current[0]
                
            # Read charge energy
            charge_energy = await client.read_holding_registers(REG_CHARGE_ENERGY, 1)
            if charge_energy:
                data["charge_energy"] = charge_energy[0]
                
            # Read charge power
            charge_power = await client.read_holding_registers(REG_CHARGE_POWER, 1)
            if charge_power:
                data["charge_power"] = charge_power[0]
                
            return data
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="olife_wallbox",
        update_method=async_update_data,
        update_interval=timedelta(seconds=FAST_SCAN_INTERVAL),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    entities = [
        OlifeWallboxEVStateSensor(coordinator, name, "wallbox_ev_state", device_info, device_unique_id),
        OlifeWallboxCurrentLimitSensor(coordinator, name, "current_limit", device_info, device_unique_id),
        OlifeWallboxMaxStationCurrentSensor(coordinator, name, "max_station_current", device_info, device_unique_id),
        OlifeWallboxLedPwmSensor(coordinator, name, "led_pwm", device_info, device_unique_id),
        OlifeWallboxChargeCurrentSensor(coordinator, name, "charge_current", device_info, device_unique_id),
        OlifeWallboxChargeEnergySensor(coordinator, name, "charge_energy", device_info, device_unique_id),
        OlifeWallboxChargePowerSensor(coordinator, name, "charge_power", device_info, device_unique_id),
    ]
    
    async_add_entities(entities)

class OlifeWallboxSensor(CoordinatorEntity, SensorEntity):
    """Base class for Olife Energy Wallbox sensors."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
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

class OlifeWallboxEVStateSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox EV state."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "EV State"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key) if self._key in self.coordinator.data else None

class OlifeWallboxCurrentLimitSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox current limit."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Current Limit"

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

class OlifeWallboxMaxStationCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox maximum station current."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Max Station Current"

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

class OlifeWallboxLedPwmSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox LED PWM."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "LED PWM"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

class OlifeWallboxChargeCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charge current."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Current"

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

class OlifeWallboxChargeEnergySensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charge energy."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Energy"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.WATT_HOUR

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

class OlifeWallboxChargePowerSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charge power."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Power"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.POWER

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT 