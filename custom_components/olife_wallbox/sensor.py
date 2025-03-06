"""Sensor platform for Olife Energy Wallbox integration."""
import logging
from datetime import timedelta, datetime
from typing import Optional, Any, Dict
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
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

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
    # State mappings
    WALLBOX_EV_STATES,
    WALLBOX_EV_STATE_ICONS,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

# Error count threshold for reducing log spam
ERROR_LOG_THRESHOLD = 10

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
        OlifeWallboxDailyChargeEnergySensor(coordinator, name, "charge_energy", device_info, device_unique_id),
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

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._raw_state = None
        self._error_count = 0
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return "EV State"

    @property
    def native_value(self):
        """Return the state of the sensor as human-readable text."""
        if not self.available:
            return None
            
        raw_state = self.coordinator.data.get(self._key)
        if raw_state is None:
            return None
            
        self._raw_state = raw_state
        
        # Convert state to human-readable text
        if raw_state in WALLBOX_EV_STATES:
            return WALLBOX_EV_STATES[raw_state]
        else:
            if self._should_log_error():
                _LOGGER.warning("Unknown EV state value: %s", raw_state)
            return f"Unknown ({raw_state})"
            
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if self._raw_state is None:
            return {}
            
        return {
            "raw_state": self._raw_state,
            "state_code": self._raw_state,
        }
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the EV state."""
        if not self.available or self._raw_state is None:
            return "mdi:help-circle-outline"
            
        return WALLBOX_EV_STATE_ICONS.get(
            self._raw_state, 
            "mdi:help-circle-outline"
        )
        
    @property
    def state_class(self):
        """Return the state class."""
        return None

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

class OlifeWallboxDailyChargeEnergySensor(OlifeWallboxSensor, RestoreEntity):
    """Sensor for Olife Energy Wallbox daily charge energy."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the daily energy sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._daily_energy = 0.0
        self._last_energy = None
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._unsub_midnight = None
        self._today = dt_util.now().date()

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._daily_energy = float(last_state.state)
                # Get the date from the attributes if available
                if "date" in last_state.attributes:
                    stored_date = dt_util.parse_date(last_state.attributes["date"])
                    if stored_date and stored_date != self._today:
                        _LOGGER.debug("Resetting daily energy counter due to date change")
                        self._daily_energy = 0.0
            except (ValueError, TypeError) as ex:
                _LOGGER.warning("Failed to restore daily energy state: %s", ex)
        
        # Register a daily callback to reset the counter at midnight
        @callback
        def midnight_callback(_):
            """Reset counter at midnight."""
            self._daily_energy = 0.0
            self._today = dt_util.now().date()
            self.async_write_ha_state()
            _LOGGER.debug("Daily energy counter reset at midnight")
            
        self._unsub_midnight = async_track_time_change(
            self.hass, midnight_callback, hour=0, minute=0, second=0
        )
        
        # Register coordinator update callback
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.hass.async_create_task(self._async_update())
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        await super().async_will_remove_from_hass()
        if self._unsub_midnight is not None:
            self._unsub_midnight()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Daily Charge Energy"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_daily_{self._key}"

    @property
    def native_value(self):
        """Return the daily energy consumption."""
        return round(self._daily_energy, 2)
        
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "date": self._today.isoformat(),
            "last_reset": dt_util.start_of_local_day().isoformat(),
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:battery-charging-outline"

    async def _async_update(self) -> None:
        """Update the daily energy counter using the session energy."""
        if not self.available:
            return
            
        current_energy = self.coordinator.data.get(self._key)
        
        if current_energy is None:
            return
            
        # If this is the first reading, just store the value
        if self._last_energy is None:
            self._last_energy = current_energy
            return
            
        # Check if the session energy has been reset (new session started)
        # or increased (continuing session)
        if current_energy < self._last_energy:
            # New session - add the last complete session to the daily total
            _LOGGER.debug(
                "New charging session detected. Adding %s Wh to daily total.", 
                self._last_energy
            )
            self._daily_energy += self._last_energy
            self._last_energy = current_energy
        else:
            # Session continuing - update the last energy value
            self._last_energy = current_energy
            
        self.async_write_ha_state() 