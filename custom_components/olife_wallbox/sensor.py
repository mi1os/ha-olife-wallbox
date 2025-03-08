"""Sensor platform for Olife Energy Wallbox integration."""
import logging
from datetime import timedelta, datetime
from typing import Optional, Any, Dict
import async_timeout
import asyncio

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
from homeassistant.helpers.event import async_track_time_change, async_track_point_in_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    FAST_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    # Register addresses
    REG_WALLBOX_EV_STATE,
    REG_CURRENT_LIMIT,
    REG_MAX_STATION_CURRENT,
    REG_LED_PWM,
    REG_CHARGE_CURRENT,
    REG_CHARGE_ENERGY,
    REG_CHARGE_POWER,
    REG_ERROR,
    REG_CP_STATE,
    REG_PREV_CP_STATE,
    REG_POWER_L1,
    REG_CURRENT_L1,
    REG_VOLTAGE_L1,
    REG_ENERGY_L1,
    REG_ENERGY_L2,
    REG_ENERGY_L3,
    REG_ENERGY_SUM,
    REG_POWER_SUM,
    REG_ENERGY_FLASH,
    # State mappings
    WALLBOX_EV_STATES,
    WALLBOX_EV_STATE_ICONS,
    CP_STATES,
    CP_STATE_ICONS,
    # Configuration options
    CONF_ENABLE_PHASE_SENSORS,
    CONF_ENABLE_ERROR_SENSORS,
    CONF_ENABLE_DAILY_ENERGY,
    CONF_ENABLE_MONTHLY_ENERGY,
    CONF_ENABLE_YEARLY_ENERGY,
    DEFAULT_ENABLE_PHASE_SENSORS,
    DEFAULT_ENABLE_ERROR_SENSORS,
    DEFAULT_ENABLE_DAILY_ENERGY,
    DEFAULT_ENABLE_MONTHLY_ENERGY,
    DEFAULT_ENABLE_YEARLY_ENERGY,
    # Connector 2 registers
    REG_WALLBOX_EV_STATE_2,
    REG_ERROR_2,
    REG_CP_STATE_2,
    REG_PREV_CP_STATE_2,
    REG_POWER_L1_2,
    REG_CURRENT_L1_2,
    REG_VOLTAGE_L1_2,
    REG_ENERGY_L1_2,
    REG_ENERGY_L2_2,
    REG_ENERGY_L3_2,
    REG_ENERGY_SUM_2,
    REG_POWER_SUM_2,
    REG_ENERGY_FLASH_2,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

# Error count threshold for reducing log spam
ERROR_LOG_THRESHOLD = 10

def start_of_local_month() -> datetime:
    """Return a datetime object representing the start of the current month."""
    now = dt_util.now()
    return dt_util.start_of_local_day(
        datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
    )

def start_of_next_month() -> datetime:
    """Return a datetime object representing the start of the next month."""
    now = dt_util.now()
    year = now.year
    month = now.month + 1
    if month > 12:
        month = 1
        year += 1
    return dt_util.start_of_local_day(
        datetime(year, month, 1, tzinfo=now.tzinfo)
    )

def start_of_next_year() -> datetime:
    """Return a datetime object representing the start of the next year."""
    now = dt_util.now()
    year = now.year + 1
    return dt_util.start_of_local_day(
        datetime(year, 1, 1, tzinfo=now.tzinfo)
    )

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Olife Energy Wallbox sensors."""
    # Get configuration and data from entry
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data.get("client")
    device_info = entry_data.get("device_info", {})
    
    # Get the number of connectors from device info
    num_connectors = device_info.get("num_connectors", 1)
    
    # Create a unique ID for the device
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 502)
    slave_id = entry.data.get(CONF_SLAVE_ID, 1)
    device_unique_id = f"{host}_{port}_{slave_id}"
    
    # Get device name
    name = entry.data.get(CONF_NAME, "Olife Wallbox")
    
    # Get configuration options
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    enable_phase_sensors = entry.options.get(CONF_ENABLE_PHASE_SENSORS, DEFAULT_ENABLE_PHASE_SENSORS)
    enable_error_sensors = entry.options.get(CONF_ENABLE_ERROR_SENSORS, DEFAULT_ENABLE_ERROR_SENSORS)
    enable_daily_energy = entry.options.get(CONF_ENABLE_DAILY_ENERGY, DEFAULT_ENABLE_DAILY_ENERGY)
    enable_monthly_energy = entry.options.get(CONF_ENABLE_MONTHLY_ENERGY, DEFAULT_ENABLE_MONTHLY_ENERGY)
    enable_yearly_energy = entry.options.get(CONF_ENABLE_YEARLY_ENERGY, DEFAULT_ENABLE_YEARLY_ENERGY)
    
    # Create enhanced device info with the information we collected
    enhanced_device_info = DeviceInfo(
        identifiers={(DOMAIN, device_unique_id)},
        name=name,
        manufacturer="Olife Energy",
        model=device_info.get("model", "Wallbox"),
        sw_version=device_info.get("sw_version", "Unknown"),
        hw_version=device_info.get("hw_version", "Unknown"),
        serial_number=device_info.get("serial_number", None),
    )
    
    # Define update coordinator function
    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            # Check if client is available and try to connect if not
            if not client._connected:
                if not await client.connect():
                    _LOGGER.warning("Failed to connect to device, some sensors may be unavailable")
            
            # If we still have too many consecutive errors, try to reset the connection
            if client.consecutive_errors > 5:
                _LOGGER.warning(
                    "Detected %s consecutive errors, attempting to reset connection",
                    client.consecutive_errors
                )
                await client.disconnect()
                await asyncio.sleep(1)
                if not await client.connect():
                    _LOGGER.error("Failed to reset connection after multiple errors")
                    return {}
                else:
                    _LOGGER.info("Successfully reset connection after multiple errors")
            
            # Create a data object to store all fetched values
            data = {}
            
            # First connector data (always available)
            data["connector_1"] = {}

            # Read wallbox state
            wallbox_ev_state = await client.read_holding_registers(REG_WALLBOX_EV_STATE, 1)
            
            # Read current limit
            current_limit = await client.read_holding_registers(REG_CURRENT_LIMIT, 1)
            
            # Read charge current (same as current limit in this register mapping)
            charge_current = await client.read_holding_registers(REG_CHARGE_CURRENT, 1)
            
            # Read max station current (which is the PP current limit)
            max_station_current = await client.read_holding_registers(REG_MAX_STATION_CURRENT, 1)
            
            # Read LED PWM (global setting)
            led_pwm = await client.read_holding_registers(REG_LED_PWM, 1)

            # Store the values in the data dictionary if they are valid
            if wallbox_ev_state is not None:
                data["connector_1"]["wallbox_ev_state"] = wallbox_ev_state[0]
                
            if current_limit is not None:
                data["connector_1"]["current_limit"] = current_limit[0]
                
            if charge_current is not None:
                data["connector_1"]["charge_current"] = charge_current[0]
                
            if max_station_current is not None:
                data["connector_1"]["max_station_current"] = max_station_current[0]
                
            if led_pwm is not None:
                data["connector_1"]["led_pwm"] = led_pwm[0]
                
            # Read total energy (as charge energy)
            energy_sum = await client.read_holding_registers(REG_ENERGY_SUM, 1)
            if energy_sum is not None:
                data["connector_1"]["charge_energy"] = energy_sum[0]
                
            # Read power of phase 1 (as charge power for simplicity)
            power_l1 = await client.read_holding_registers(REG_POWER_L1, 1)
            if power_l1 is not None:
                data["connector_1"]["charge_power"] = power_l1[0]
            
            # Read the summary energy value
            energy_sum_extended = await client.read_holding_registers(REG_ENERGY_SUM, 2)
            if energy_sum_extended is not None and len(energy_sum_extended) >= 2:
                data["connector_1"]["energy_sum"] = energy_sum_extended[0] + (energy_sum_extended[1] << 16)
                
            # Only read error and CP state sensors if enabled
            if enable_error_sensors:
                # Read error code
                error_code = await client.read_holding_registers(REG_ERROR, 1)
                
                # Read CP state
                cp_state = await client.read_holding_registers(REG_CP_STATE, 1)
                
                # Read Previous CP state
                prev_cp_state = await client.read_holding_registers(REG_PREV_CP_STATE, 1)
                
                # Add the error register values to the data
                if error_code is not None:
                    data["connector_1"]["error_code"] = error_code[0]
                    
                if cp_state is not None:
                    data["connector_1"]["cp_state"] = cp_state[0]
                    
                if prev_cp_state is not None:
                    data["connector_1"]["prev_cp_state"] = prev_cp_state[0]
            
            # Only read phase measurements if enabled
            if enable_phase_sensors:
                # Read phase power measurements
                power_phases = await client.read_holding_registers(REG_POWER_L1, 3)
                
                # Read total power (sum of all phases)
                power_sum = await client.read_holding_registers(REG_POWER_SUM, 1)
                
                # Read phase current measurements
                current_phases = await client.read_holding_registers(REG_CURRENT_L1, 3)
                
                # Read phase voltage measurements
                voltage_phases = await client.read_holding_registers(REG_VOLTAGE_L1, 3)
                
                # Read phase energy measurements
                energy_phases = []
                energy_l1 = await client.read_holding_registers(REG_ENERGY_L1, 2)
                energy_l2 = await client.read_holding_registers(REG_ENERGY_L2, 2)
                energy_l3 = await client.read_holding_registers(REG_ENERGY_L3, 2)
                
                # Read energy flash (saved to flash every 24 hours)
                energy_flash = await client.read_holding_registers(REG_ENERGY_FLASH, 2)
                
                if energy_l1 is not None and len(energy_l1) >= 2:
                    energy_phases.append(energy_l1[0] + (energy_l1[1] << 16))
                else:
                    energy_phases.append(None)
                    
                if energy_l2 is not None and len(energy_l2) >= 2:
                    energy_phases.append(energy_l2[0] + (energy_l2[1] << 16))
                else:
                    energy_phases.append(None)
                    
                if energy_l3 is not None and len(energy_l3) >= 2:
                    energy_phases.append(energy_l3[0] + (energy_l3[1] << 16))
                else:
                    energy_phases.append(None)
                
                # Add phase measurements to data
                if power_phases is not None and len(power_phases) >= 3:
                    data["connector_1"]["power_l1"] = power_phases[0]
                    data["connector_1"]["power_l2"] = power_phases[1]
                    data["connector_1"]["power_l3"] = power_phases[2]
                
                # Add total power
                if power_sum is not None:
                    data["connector_1"]["power_sum"] = power_sum[0]
                
                if current_phases is not None and len(current_phases) >= 3:
                    data["connector_1"]["current_l1"] = current_phases[0]
                    data["connector_1"]["current_l2"] = current_phases[1]
                    data["connector_1"]["current_l3"] = current_phases[2]
                
                if voltage_phases is not None and len(voltage_phases) >= 3:
                    data["connector_1"]["voltage_l1"] = voltage_phases[0]
                    data["connector_1"]["voltage_l2"] = voltage_phases[1]
                    data["connector_1"]["voltage_l3"] = voltage_phases[2]
                
                if energy_phases is not None and len(energy_phases) >= 3:
                    if energy_phases[0] is not None:
                        data["connector_1"]["energy_l1"] = energy_phases[0]
                    if energy_phases[1] is not None:
                        data["connector_1"]["energy_l2"] = energy_phases[1]
                    if energy_phases[2] is not None:
                        data["connector_1"]["energy_l3"] = energy_phases[2]
                
                # Add energy flash
                if energy_flash is not None and len(energy_flash) >= 2:
                    data["connector_1"]["energy_flash"] = energy_flash[0] + (energy_flash[1] << 16)
            
            # If we have two connectors, read data for the second connector
            if num_connectors > 1:
                _LOGGER.debug("Reading data for second connector")
                data["connector_2"] = {}
                
                # Second connector data
                wallbox_ev_state_2 = await client.read_holding_registers(REG_WALLBOX_EV_STATE_2, 1)
                current_limit_2 = await client.read_holding_registers(REG_CURRENT_LIMIT_2, 1)
                charge_current_2 = await client.read_holding_registers(REG_CHARGE_CURRENT_2, 1)
                max_station_current_2 = await client.read_holding_registers(REG_MAX_STATION_CURRENT_2, 1)
                
                if wallbox_ev_state_2 is not None:
                    data["connector_2"]["wallbox_ev_state"] = wallbox_ev_state_2[0]
                    
                if current_limit_2 is not None:
                    data["connector_2"]["current_limit"] = current_limit_2[0]
                    
                if charge_current_2 is not None:
                    data["connector_2"]["charge_current"] = charge_current_2[0]
                    
                if max_station_current_2 is not None:
                    data["connector_2"]["max_station_current"] = max_station_current_2[0]
                
                # Use the same LED PWM value for connector 2 (it's a global setting)
                if led_pwm is not None:
                    data["connector_2"]["led_pwm"] = led_pwm[0]
                
                # Read total energy (as charge energy) for connector 2
                energy_sum_2 = await client.read_holding_registers(REG_ENERGY_SUM_2, 1)
                if energy_sum_2 is not None:
                    data["connector_2"]["charge_energy"] = energy_sum_2[0]
                
                # Read power of phase 1 (as charge power for simplicity) for connector 2
                power_l1_2 = await client.read_holding_registers(REG_POWER_L1_2, 1)
                if power_l1_2 is not None:
                    data["connector_2"]["charge_power"] = power_l1_2[0]
                
                # Only read error and CP state sensors if enabled
                if enable_error_sensors:
                    error_code_2 = await client.read_holding_registers(REG_ERROR_2, 1)
                    cp_state_2 = await client.read_holding_registers(REG_CP_STATE_2, 1)
                    prev_cp_state_2 = await client.read_holding_registers(REG_PREV_CP_STATE_2, 1)
                    
                    if error_code_2 is not None:
                        data["connector_2"]["error_code"] = error_code_2[0]
                        
                    if cp_state_2 is not None:
                        data["connector_2"]["cp_state"] = cp_state_2[0]
                        
                    if prev_cp_state_2 is not None:
                        data["connector_2"]["prev_cp_state"] = prev_cp_state_2[0]
                
                # Only read phase measurements if enabled
                if enable_phase_sensors:
                    power_phases_2 = await client.read_holding_registers(REG_POWER_L1_2, 3)
                    
                    # Read total power (sum of all phases) for connector 2
                    power_sum_2 = await client.read_holding_registers(REG_POWER_SUM_2, 1)
                    
                    current_phases_2 = await client.read_holding_registers(REG_CURRENT_L1_2, 3)
                    voltage_phases_2 = await client.read_holding_registers(REG_VOLTAGE_L1_2, 3)
                    
                    energy_phases_2 = []
                    energy_l1_2 = await client.read_holding_registers(REG_ENERGY_L1_2, 2)
                    energy_l2_2 = await client.read_holding_registers(REG_ENERGY_L2_2, 2)
                    energy_l3_2 = await client.read_holding_registers(REG_ENERGY_L3_2, 2)
                    
                    # Read energy flash for connector 2
                    energy_flash_2 = await client.read_holding_registers(REG_ENERGY_FLASH_2, 2)
                    
                    if energy_l1_2 is not None and len(energy_l1_2) >= 2:
                        energy_phases_2.append(energy_l1_2[0] + (energy_l1_2[1] << 16))
                    else:
                        energy_phases_2.append(None)
                        
                    if energy_l2_2 is not None and len(energy_l2_2) >= 2:
                        energy_phases_2.append(energy_l2_2[0] + (energy_l2_2[1] << 16))
                    else:
                        energy_phases_2.append(None)
                        
                    if energy_l3_2 is not None and len(energy_l3_2) >= 2:
                        energy_phases_2.append(energy_l3_2[0] + (energy_l3_2[1] << 16))
                    else:
                        energy_phases_2.append(None)
                    
                    # Add phase measurements to data
                    if power_phases_2 is not None and len(power_phases_2) >= 3:
                        data["connector_2"]["power_l1"] = power_phases_2[0]
                        data["connector_2"]["power_l2"] = power_phases_2[1]
                        data["connector_2"]["power_l3"] = power_phases_2[2]
                    
                    # Add total power for connector 2
                    if power_sum_2 is not None:
                        data["connector_2"]["power_sum"] = power_sum_2[0]
                    
                    if current_phases_2 is not None and len(current_phases_2) >= 3:
                        data["connector_2"]["current_l1"] = current_phases_2[0]
                        data["connector_2"]["current_l2"] = current_phases_2[1]
                        data["connector_2"]["current_l3"] = current_phases_2[2]
                    
                    if voltage_phases_2 is not None and len(voltage_phases_2) >= 3:
                        data["connector_2"]["voltage_l1"] = voltage_phases_2[0]
                        data["connector_2"]["voltage_l2"] = voltage_phases_2[1]
                        data["connector_2"]["voltage_l3"] = voltage_phases_2[2]
                    
                    if energy_phases_2 is not None and len(energy_phases_2) >= 3:
                        if energy_phases_2[0] is not None:
                            data["connector_2"]["energy_l1"] = energy_phases_2[0]
                        if energy_phases_2[1] is not None:
                            data["connector_2"]["energy_l2"] = energy_phases_2[1]
                        if energy_phases_2[2] is not None:
                            data["connector_2"]["energy_l3"] = energy_phases_2[2]
                    
                    # Add energy flash for connector 2
                    if energy_flash_2 is not None and len(energy_flash_2) >= 2:
                        data["connector_2"]["energy_flash"] = energy_flash_2[0] + (energy_flash_2[1] << 16)
                
                # Read the summary energy value for connector 2
                energy_sum_2_extended = await client.read_holding_registers(REG_ENERGY_SUM_2, 2)
                if energy_sum_2_extended is not None and len(energy_sum_2_extended) >= 2:
                    data["connector_2"]["energy_sum"] = energy_sum_2_extended[0] + (energy_sum_2_extended[1] << 16)
            
            return data
        except Exception as exception:
            _LOGGER.error("Error updating data: %s", exception)
            raise UpdateFailed(f"Error updating data: {exception}") from exception

    # Create coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{name} Sensor",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data so we have data when entities initialize
    await coordinator.async_config_entry_first_refresh()
    
    # Store the coordinator in the hass data
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    entities = []
    
    # Create entity for each connector
    for connector_idx in range(1, num_connectors + 1):
        connector_key = f"connector_{connector_idx}"
        connector_name = f"{name}" if num_connectors == 1 else f"{name} Connector {connector_idx}"
        
        # Add a suffix to the device_unique_id if we have multiple connectors
        connector_unique_id = device_unique_id if num_connectors == 1 else f"{device_unique_id}_connector_{connector_idx}"
        
        # Create a device_info object per connector
        connector_device_info = DeviceInfo(
            identifiers={(DOMAIN, connector_unique_id)},
            name=connector_name,
            manufacturer="Olife Energy",
            model=device_info.get("model", "Wallbox"),
            sw_version=device_info.get("sw_version", "Unknown"),
            hw_version=device_info.get("hw_version", "Unknown"),
            via_device=(DOMAIN, device_unique_id) if num_connectors > 1 else None,
        )
        
        # Base sensors (always created)
        entities.extend([
            OlifeWallboxEVStateSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.wallbox_ev_state", 
                connector_device_info, 
                f"{connector_unique_id}_wallbox_ev_state"
            ),
            OlifeWallboxCurrentLimitSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.current_limit", 
                connector_device_info, 
                f"{connector_unique_id}_current_limit"
            ),
            OlifeWallboxMaxStationCurrentSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.max_station_current", 
                connector_device_info, 
                f"{connector_unique_id}_max_station_current"
            ),
            OlifeWallboxLedPwmSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.led_pwm", 
                connector_device_info, 
                f"{connector_unique_id}_led_pwm"
            ),
            OlifeWallboxChargeCurrentSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.charge_current", 
                connector_device_info, 
                f"{connector_unique_id}_charge_current"
            ),
            OlifeWallboxChargeEnergySensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.charge_energy", 
                connector_device_info, 
                f"{connector_unique_id}_charge_energy"
            ),
            OlifeWallboxChargePowerSensor(
                coordinator, 
                connector_name, 
                f"{connector_key}.charge_power", 
                connector_device_info, 
                f"{connector_unique_id}_charge_power"
            )
        ])
        
        # Add error sensors if enabled
        if enable_error_sensors:
            entities.extend([
                OlifeWallboxErrorCodeSensor(
                    coordinator, 
                    connector_name, 
                    f"{connector_key}.error_code", 
                    connector_device_info, 
                    f"{connector_unique_id}_error_code"
                ),
                OlifeWallboxCPStateSensor(
                    coordinator, 
                    connector_name, 
                    f"{connector_key}.cp_state", 
                    connector_device_info, 
                    f"{connector_unique_id}_cp_state"
                )
            ])
        
        # Add phase sensors if enabled
        if enable_phase_sensors:
            for phase_num in range(1, 4):
                entities.extend([
                    OlifeWallboxPhasePowerSensor(
                        coordinator, 
                        connector_name, 
                        f"{connector_key}.power_l{phase_num}", 
                        connector_device_info, 
                        f"{connector_unique_id}_power_l{phase_num}", 
                        phase_num
                    ),
                    OlifeWallboxPhaseCurrentSensor(
                        coordinator, 
                        connector_name, 
                        f"{connector_key}.current_l{phase_num}", 
                        connector_device_info, 
                        f"{connector_unique_id}_current_l{phase_num}", 
                        phase_num
                    ),
                    OlifeWallboxPhaseVoltageSensor(
                        coordinator, 
                        connector_name, 
                        f"{connector_key}.voltage_l{phase_num}", 
                        connector_device_info, 
                        f"{connector_unique_id}_voltage_l{phase_num}", 
                        phase_num
                    ),
                    OlifeWallboxPhaseEnergySensor(
                        coordinator, 
                        connector_name, 
                        f"{connector_key}.energy_l{phase_num}", 
                        connector_device_info, 
                        f"{connector_unique_id}_energy_l{phase_num}", 
                        phase_num
                    )
                ])
        
        # Add energy tracking sensors if enabled
        if enable_daily_energy:
            entities.append(
                OlifeWallboxDailyChargeEnergySensor(
                    coordinator, 
                    connector_name, 
                    f"{connector_key}.charge_power", 
                    connector_device_info, 
                    f"{connector_unique_id}_daily_charge_energy"
                )
            )
            
        if enable_monthly_energy:
            entities.append(
                OlifeWallboxMonthlyChargeEnergySensor(
                    coordinator, 
                    connector_name, 
                    f"{connector_key}.charge_power", 
                    connector_device_info, 
                    f"{connector_unique_id}_monthly_charge_energy"
                )
            )
            
        if enable_yearly_energy:
            entities.append(
                OlifeWallboxYearlyChargeEnergySensor(
                    coordinator, 
                    connector_name, 
                    f"{connector_key}.charge_power", 
                    connector_device_info, 
                    f"{connector_unique_id}_yearly_charge_energy"
                )
            )
    
    # Add the entities to Home Assistant
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
        if not self.coordinator.last_update_success:
            return False
            
        # Handle nested keys (e.g., "connector_1.wallbox_ev_state")
        if '.' in self._key:
            parts = self._key.split('.')
            data = self.coordinator.data
            
            # Traverse the nested dictionary
            for part in parts:
                if not isinstance(data, dict) or part not in data:
                    return False
                data = data[part]
                
            return True
        else:
            # Direct key
            return self._key in self.coordinator.data

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_{self._key}"
        
    @property
    def device_info(self):
        """Return device information."""
        return self._device_info

    def _get_value_from_data(self, key=None):
        """Get a value from the data dictionary, handling nested keys."""
        if key is None:
            key = self._key
            
        if not self.coordinator.data:
            return None
            
        # Handle nested keys (e.g., "connector_1.wallbox_ev_state")
        if '.' in key:
            parts = key.split('.')
            data = self.coordinator.data
            
            # Traverse the nested dictionary
            for part in parts:
                if not isinstance(data, dict) or part not in data:
                    return None
                data = data[part]
                
            return data
        else:
            # Direct key
            return self.coordinator.data.get(key)

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
            
        raw_state = self._get_value_from_data()
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
        return self._get_value_from_data()

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
        return self._get_value_from_data()

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
        return self._get_value_from_data()

class OlifeWallboxChargeCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charge current."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Current"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._get_value_from_data()

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
        return self._get_value_from_data()

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
        return self._get_value_from_data()

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
        
        # Listen for reset events from the service
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_reset_counter", self._handle_reset_event
            )
        )
        
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
    def _handle_reset_event(self, event):
        """Handle reset event from service."""
        if (
            event.data
            and "entity_id" in event.data
            and "device_id" in event.data
            and self.entity_id == event.data["entity_id"]
        ):
            _LOGGER.info("Resetting daily energy counter from service call")
            self._daily_energy = 0.0
            self.async_write_ha_state()

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
            
        current_energy = self._get_value_from_data()
        
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

class OlifeWallboxMonthlyChargeEnergySensor(OlifeWallboxSensor, RestoreEntity):
    """Sensor for Olife Energy Wallbox monthly charge energy."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the monthly energy sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._monthly_energy = 0.0
        self._last_energy = None
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._unsub_month = None
        self._month = dt_util.now().month

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Listen for reset events from the service
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_reset_counter", self._handle_reset_event
            )
        )
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._monthly_energy = float(last_state.state)
                # Get the month from the attributes if available
                if "month" in last_state.attributes:
                    stored_month = last_state.attributes["month"]
                    current_month = dt_util.now().month
                    if stored_month != current_month:
                        _LOGGER.debug("Resetting monthly energy counter due to month change")
                        self._monthly_energy = 0.0
            except (ValueError, TypeError) as ex:
                _LOGGER.warning("Failed to restore monthly energy state: %s", ex)
        
        # Register a monthly callback to reset the counter at the first day of month
        @callback
        def month_callback(_):
            """Reset counter at the first day of month."""
            self._monthly_energy = 0.0
            self._month = dt_util.now().month
            self.async_write_ha_state()
            _LOGGER.debug("Monthly energy counter reset at first day of month")
            
            # Re-register for next month
            self._unsub_month = async_track_point_in_time(
                self.hass, month_callback, start_of_next_month()
            )
            
        self._unsub_month = async_track_point_in_time(
            self.hass, month_callback, start_of_next_month()
        )
        
        # Register coordinator update callback
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_reset_event(self, event):
        """Handle reset event from service."""
        if (
            event.data
            and "entity_id" in event.data
            and "device_id" in event.data
            and self.entity_id == event.data["entity_id"]
        ):
            _LOGGER.info("Resetting monthly energy counter from service call")
            self._monthly_energy = 0.0
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.hass.async_create_task(self._async_update())
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        await super().async_will_remove_from_hass()
        if self._unsub_month is not None:
            self._unsub_month()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Monthly Charge Energy"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_monthly_{self._key}"

    @property
    def native_value(self):
        """Return the monthly energy consumption."""
        return round(self._monthly_energy, 2)
        
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "date": dt_util.now().date().isoformat(),
            "month": dt_util.now().month,
            "last_reset": start_of_local_month().isoformat(),
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:battery-charging-outline"

    async def _async_update(self) -> None:
        """Update the monthly energy counter using the session energy."""
        if not self.available:
            return
            
        current_energy = self._get_value_from_data()
        
        if current_energy is None:
            return
            
        # If this is the first reading, just store the value
        if self._last_energy is None:
            self._last_energy = current_energy
            return
            
        # Check if the session energy has been reset (new session started)
        # or increased (continuing session)
        if current_energy < self._last_energy:
            # New session - add the last complete session to the monthly total
            _LOGGER.debug(
                "New charging session detected. Adding %s Wh to monthly total.", 
                self._last_energy
            )
            self._monthly_energy += self._last_energy
            self._last_energy = current_energy
        else:
            # Session continuing - update the last energy value
            self._last_energy = current_energy
            
        self.async_write_ha_state() 

class OlifeWallboxYearlyChargeEnergySensor(OlifeWallboxSensor, RestoreEntity):
    """Sensor for Olife Energy Wallbox yearly charge energy."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the yearly energy sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._yearly_energy = 0.0
        self._last_energy = None
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._unsub_yearly = None
        self._this_year = dt_util.now().date().replace(month=1, day=1)

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Listen for reset events from the service
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_reset_counter", self._handle_reset_event
            )
        )
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._yearly_energy = float(last_state.state)
                # Get the date from the attributes if available
                if "date" in last_state.attributes:
                    stored_date = dt_util.parse_date(last_state.attributes["date"])
                    if stored_date and stored_date.year != self._this_year.year:
                        _LOGGER.debug("Resetting yearly energy counter due to year change")
                        self._yearly_energy = 0.0
            except (ValueError, TypeError) as ex:
                _LOGGER.warning("Failed to restore yearly energy state: %s", ex)
        
        # Register a yearly callback to reset the counter at the start of the year
        @callback
        def yearly_callback(_):
            """Reset counter at the start of the year."""
            self._yearly_energy = 0.0
            self._this_year = dt_util.now().date().replace(month=1, day=1)
            self.async_write_ha_state()
            _LOGGER.debug("Yearly energy counter reset at the start of the year")
            
            # Re-register for next year
            self._unsub_yearly = async_track_point_in_time(
                self.hass, yearly_callback, start_of_next_year()
            )
            
        self._unsub_yearly = async_track_point_in_time(
            self.hass, yearly_callback, start_of_next_year()
        )
        
        # Register coordinator update callback
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_reset_event(self, event):
        """Handle reset event from service."""
        if (
            event.data
            and "entity_id" in event.data
            and "device_id" in event.data
            and self.entity_id == event.data["entity_id"]
        ):
            _LOGGER.info("Resetting yearly energy counter from service call")
            self._yearly_energy = 0.0
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.hass.async_create_task(self._async_update())
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        await super().async_will_remove_from_hass()
        if self._unsub_yearly is not None:
            self._unsub_yearly()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Yearly Charge Energy"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._device_unique_id}_yearly_{self._key}"

    @property
    def native_value(self):
        """Return the yearly energy consumption."""
        # Convert to kilowatt-hours
        return round(self._yearly_energy / 1000.0, 2)
        
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        # Get the first day of the current year
        year_start = dt_util.start_of_local_day(
            datetime(self._this_year.year, 1, 1, tzinfo=dt_util.now().tzinfo)
        )
        return {
            "date": self._this_year.isoformat(),
            "last_reset": year_start.isoformat(),
            "total_watt_hours": round(self._yearly_energy, 2),
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:battery-charging-outline"

    async def _async_update(self) -> None:
        """Update the yearly energy counter using the session energy."""
        if not self.available:
            return
            
        current_energy = self._get_value_from_data()
        
        if current_energy is None:
            return
            
        # If this is the first reading, just store the value
        if self._last_energy is None:
            self._last_energy = current_energy
            return
            
        # Check if the session energy has been reset (new session started)
        # or increased (continuing session)
        if current_energy < self._last_energy:
            # New session - add the last complete session to the yearly total
            _LOGGER.debug(
                "New charging session detected. Adding %s Wh to yearly total.", 
                self._last_energy
            )
            self._yearly_energy += self._last_energy
            self._last_energy = current_energy
        else:
            # Session continuing - update the last energy value
            self._last_energy = current_energy
            
        self.async_write_ha_state() 

class OlifeWallboxCPStateSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox CP (Control Pilot) state."""

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
        return "CP State"

    @property
    def native_value(self):
        """Return the state of the sensor as human-readable text."""
        if not self.available:
            return None
            
        raw_state = self._get_value_from_data()
        if raw_state is None:
            return None
            
        self._raw_state = raw_state
        
        # Convert state to human-readable text
        if raw_state in CP_STATES:
            return CP_STATES[raw_state]
        else:
            if self._should_log_error():
                _LOGGER.warning("Unknown CP state value: %s", raw_state)
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
        """Return the icon to use in the frontend based on the CP state."""
        if not self.available or self._raw_state is None:
            return "mdi:help-circle-outline"
            
        return CP_STATE_ICONS.get(
            self._raw_state, 
            "mdi:help-circle-outline"
        )
        
    @property
    def state_class(self):
        """Return the state class."""
        return None

class OlifeWallboxErrorCodeSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox error code."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return "Error Code"

    @property
    def native_value(self):
        """Return the error code."""
        if not self.available:
            return None
            
        value = self._get_value_from_data()
        return value if value is not None else None
            
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if not self.available:
            return {}
            
        value = self._get_value_from_data()
        if value is None:
            return {}
            
        # Decode the binary error flags
        errors = []
        error_flags = value
        
        # These error flags are educated guesses based on standard practices
        # They should be updated with actual error codes from documentation
        if error_flags & 0x0001: errors.append("GFCI Fault")
        if error_flags & 0x0002: errors.append("Over Voltage")
        if error_flags & 0x0004: errors.append("Under Voltage")
        if error_flags & 0x0008: errors.append("Over Current")
        if error_flags & 0x0010: errors.append("Over Temperature")
        if error_flags & 0x0020: errors.append("Communication Error")
        if error_flags & 0x0040: errors.append("CP Signal Error")
        if error_flags & 0x0080: errors.append("Lock Error")
        if error_flags & 0x0100: errors.append("Emergency Stop")
        
        return {
            "error_code": value,
            "error_binary": f"{value:016b}",
            "active_errors": errors
        }
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if not self.available:
            return "mdi:alert-circle-outline"
            
        value = self._get_value_from_data()
        if value is None or value == 0:
            return "mdi:check-circle-outline"
        return "mdi:alert-circle"

class OlifeWallboxPhasePowerSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox phase power."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Power"

    @property
    def native_value(self):
        """Return the phase power in Watts."""
        if not self.available:
            return None
            
        return self._get_value_from_data()
            
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:flash"

class OlifeWallboxPhaseCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox phase current."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Current"

    @property
    def native_value(self):
        """Return the phase current in Amps (converting from mA)."""
        if not self.available:
            return None
            
        milliamps = self._get_value_from_data()
        if milliamps is None:
            return None
            
        # Convert from mA to A
        return round(milliamps / 1000.0, 2)
            
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfElectricCurrent.AMPERE
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:current-ac"

class OlifeWallboxPhaseVoltageSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox phase voltage."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Voltage"

    @property
    def native_value(self):
        """Return the phase voltage in Volts (converting from decivolts)."""
        if not self.available:
            return None
            
        decivolts = self._get_value_from_data()
        if decivolts is None:
            return None
            
        # Convert from 0.1V to V
        return round(decivolts / 10.0, 1)
            
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "V"
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lightning-bolt"

class OlifeWallboxPhaseEnergySensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox phase energy."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Energy"

    @property
    def native_value(self):
        """Return the phase energy in kWh (converting from mWh)."""
        if not self.available:
            return None
            
        milliwatthours = self._get_value_from_data()
        if milliwatthours is None:
            return None
            
        # Convert from mWh to kWh
        return round(milliwatthours / 1000000.0, 3)
            
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lightning-bolt"
        
    @property
    def last_reset(self):
        """Return the time when the sensor was last reset."""
        # This is a total_increasing sensor, so it's never reset
        return None 