"""Sensor platform for Olife Energy Wallbox integration."""
import logging
from datetime import timedelta
from typing import Optional, Any, Dict
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
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_time_change, async_track_point_in_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    CONF_ENABLE_PHASE_SENSORS,
    DEFAULT_ENABLE_PHASE_SENSORS,
    CONF_ENABLE_ERROR_SENSORS,
    DEFAULT_ENABLE_ERROR_SENSORS,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    MAX_CONSECUTIVE_ERRORS,
    REG_WALLBOX_EV_STATE_A,
    REG_WALLBOX_EV_STATE_B,
    REG_CURRENT_LIMIT_A,
    REG_CURRENT_LIMIT_B,
    REG_CHARGE_CURRENT_A,
    REG_CHARGE_CURRENT_B,
    REG_CHARGE_ENERGY_A,
    REG_CHARGE_ENERGY_B,
    REG_CHARGE_POWER_A,
    REG_CHARGE_POWER_B,
    REG_ERROR_A,
    REG_ERROR_B,
    REG_CP_STATE_A,
    REG_CP_STATE_B,
    REG_PREV_CP_STATE_A,
    REG_PREV_CP_STATE_B,
    REG_MAX_STATION_CURRENT,
    REG_LED_PWM,
    REG_ENERGY_SUM_A,
    REG_ENERGY_SUM_B,
    REG_POWER_L1_A,
    REG_POWER_L1_B,
    REG_POWER_L2_A,
    REG_POWER_L2_B,
    REG_POWER_L3_A,
    REG_POWER_L3_B,
    REG_POWER_SUM_A,
    REG_POWER_SUM_B,
    REG_CURRENT_L1_A,
    REG_CURRENT_L1_B,
    REG_CURRENT_L2_A,
    REG_CURRENT_L2_B,
    REG_CURRENT_L3_A,
    REG_CURRENT_L3_B,
    REG_VOLTAGE_L1_A,
    REG_VOLTAGE_L1_B,
    REG_VOLTAGE_L2_A,
    REG_VOLTAGE_L2_B,
    REG_VOLTAGE_L3_A,
    REG_VOLTAGE_L3_B,
    REG_ENERGY_L1_A,
    REG_ENERGY_L1_B,
    REG_ENERGY_L2_A,
    REG_ENERGY_L2_B,
    REG_ENERGY_L3_A,
    REG_ENERGY_L3_B,
    REG_ENERGY_FLASH_A,
    REG_ENERGY_FLASH_B,
    REG_EXTERNAL_WATTMETER,
    WALLBOX_EV_STATES,
    WALLBOX_EV_STATE_DESCRIPTIONS,
    WALLBOX_EV_STATE_ICONS,
    CP_STATES,
    CP_STATE_DESCRIPTIONS,
    CP_STATE_ICONS,
    REG_EXT_ENERGY_L1,
    REG_EXT_ENERGY_L2,
    REG_EXT_ENERGY_L3,
    REG_EXT_ENERGY_TOTAL,
    REG_EXT_ENERGY_SAVED_FLASH,
    REG_EXT_POWER_L1,
    REG_EXT_POWER_L2,
    REG_EXT_POWER_L3,
    REG_EXT_POWER_SUM,
    REG_EXT_CURRENT_L1,
    REG_EXT_CURRENT_L2,
    REG_EXT_CURRENT_L3,
    REG_EXT_VOLTAGE_L1,
    REG_EXT_VOLTAGE_L2,
    REG_EXT_VOLTAGE_L3,
    ERROR_LOG_THRESHOLD
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
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
    async def async_update_data() -> Dict[str, Any]:
        """Fetch data from the Olife Energy Wallbox."""
        try:
            # Reuse the existing ModbusClient from hass.data
            if not await client.connect():
                # Only log connection failure on state change
                if not hasattr(async_update_data, '_last_connected') or async_update_data._last_connected:
                    _LOGGER.error("Failed to connect to Olife Wallbox at %s:%s", host, port)
                    async_update_data._last_connected = False
                return {}
            
            # Log successful reconnection
            if hasattr(async_update_data, '_last_connected') and not async_update_data._last_connected:
                _LOGGER.info("Successfully reconnected to Olife Wallbox at %s:%s", host, port)
            async_update_data._last_connected = True
            
            # Check if the client has too many consecutive errors
            if client.consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                # Only log on state change
                if not hasattr(async_update_data, '_reset_attempted') or not async_update_data._reset_attempted:
                    _LOGGER.warning("Too many consecutive errors (%s), attempting connection reset", client.consecutive_errors)
                    async_update_data._reset_attempted = True
                    
                await client.disconnect()
                await asyncio.sleep(1)
                if not await client.connect():
                    _LOGGER.debug("Failed to reset connection after multiple errors (will retry)")
                    return {}
                else:
                    _LOGGER.info("Successfully reset connection after multiple errors")
                    async_update_data._reset_attempted = False
            
            # Create a data object to store all fetched values
            data = {}
            
            # Check if the external wattmeter is present
            external_wattmeter = await client.read_holding_registers(REG_EXTERNAL_WATTMETER, 1)
            if external_wattmeter is not None:
                # Get the current status
                external_wattmeter_present = (external_wattmeter[0] == 1)
                
                # Check if status has changed, or if this is the first time we're checking
                if not hasattr(async_update_data, 'last_external_wattmeter_status') or \
                   async_update_data.last_external_wattmeter_status != external_wattmeter_present:
                    
                    # Log status change or initial status
                    status_text = "Present" if external_wattmeter_present else "Not present"
                    if hasattr(async_update_data, 'last_external_wattmeter_status'):
                        _LOGGER.info("External wattmeter status changed to: %s (register value: %s)", 
                                   status_text, external_wattmeter[0])
                    else:
                        _LOGGER.info("External wattmeter status: %s (register value: %s)", 
                                   status_text, external_wattmeter[0])
                    
                    # Save the status for future reference
                    async_update_data.last_external_wattmeter_status = external_wattmeter_present
                
                # Store the status for entity use
                data["external_wattmeter_present"] = external_wattmeter_present
            else:
                # Handle error case
                if not hasattr(async_update_data, 'last_external_wattmeter_status') or \
                   async_update_data.last_external_wattmeter_status is not False:
                    _LOGGER.warning("Could not read external wattmeter status, assuming not present")
                    async_update_data.last_external_wattmeter_status = False
                
                data["external_wattmeter_present"] = False
            
            # Get the number of connectors and determine which ones to use
            connectors_in_use = device_info.get("connectors_in_use", ["B"])
            
            # Initialize data structure for each connector
            # IMPORTANT: We use letter-based naming convention for connectors:
            # - connector_A: left side connector
            # - connector_B: right side connector
            # This standardization reduces confusion and matches physical labeling.
            
            # For single-connector Wallboxes, we only use the B connector registers (right side)
            if num_connectors == 1:
                data["connector_B"] = {}
                
                # Read from the B connector registers
                wallbox_ev_state = await client.read_holding_registers(REG_WALLBOX_EV_STATE_B, 1)
                current_limit = await client.read_holding_registers(REG_CURRENT_LIMIT_B, 1)
                charge_current = await client.read_holding_registers(REG_CHARGE_CURRENT_B, 1)
                max_station_current = await client.read_holding_registers(REG_MAX_STATION_CURRENT, 1)
                led_pwm = await client.read_holding_registers(REG_LED_PWM, 1)
                
                # Store in connector_B only (no duplication for single-connector)
                if wallbox_ev_state is not None:
                    data["connector_B"]["wallbox_ev_state"] = wallbox_ev_state[0]
                
                if current_limit is not None:
                    data["connector_B"]["current_limit"] = current_limit[0]
                
                if charge_current is not None:
                    data["connector_B"]["charge_current"] = charge_current[0]
                
                if max_station_current is not None:
                    data["connector_B"]["max_station_current"] = max_station_current[0]
                
                if led_pwm is not None:
                    data["connector_B"]["led_pwm"] = led_pwm[0]
                
                # Read power sum (total power from all phases)
                power_sum = await client.read_holding_registers(REG_POWER_SUM_B, 1)
                if power_sum is not None:
                    data["connector_B"]["charge_power"] = power_sum[0]

                # Read the summary energy value (32-bit)
                energy_sum_extended = await client.read_holding_registers(REG_ENERGY_SUM_B, 2)
                if energy_sum_extended is not None and len(energy_sum_extended) >= 2:
                    energy_sum_value = energy_sum_extended[0] + (energy_sum_extended[1] << 16)
                    data["connector_B"]["energy_sum"] = energy_sum_value
                    # Also update charge_energy with the correct 32-bit value
                    data["connector_B"]["charge_energy"] = energy_sum_value
                
                # Only read error and CP state sensors if enabled
                if enable_error_sensors:
                    # Read error code for B connector
                    error_code = await client.read_holding_registers(REG_ERROR_B, 1)
                    cp_state = await client.read_holding_registers(REG_CP_STATE_B, 1)
                    prev_cp_state = await client.read_holding_registers(REG_PREV_CP_STATE_B, 1)
                    
                    # Store in connector_B
                    if error_code is not None:
                        data["connector_B"]["error_code"] = error_code[0]
                    
                    if cp_state is not None:
                        data["connector_B"]["cp_state"] = cp_state[0]
                    
                    if prev_cp_state is not None:
                        data["connector_B"]["prev_cp_state"] = prev_cp_state[0]
            else:
                # Dual-connector setup  
                data["connector_A"] = {}
                data["connector_B"] = {}
                # TODO: Add dual-connector reading logic here if needed
            
            # Get phase data based on external wattmeter status
            if data.get("external_wattmeter_present", False):
                # Only log this when the status changes to reduce verbosity
                if not hasattr(async_update_data, 'last_using_external_wattmeter') or \
                   async_update_data.last_using_external_wattmeter is not True:
                    _LOGGER.info("Using external wattmeter registers for phase data")
                    async_update_data.last_using_external_wattmeter = True
                
                # Use external wattmeter registers (4200-4219)
                power_registers = [REG_EXT_POWER_L1, REG_EXT_POWER_L2, REG_EXT_POWER_L3]
                current_registers = [REG_EXT_CURRENT_L1, REG_EXT_CURRENT_L2, REG_EXT_CURRENT_L3]
                voltage_registers = [REG_EXT_VOLTAGE_L1, REG_EXT_VOLTAGE_L2, REG_EXT_VOLTAGE_L3]
                energy_registers = [REG_EXT_ENERGY_L1, REG_EXT_ENERGY_L2, REG_EXT_ENERGY_L3]
            else:
                # Only log this when the status changes to reduce verbosity
                if not hasattr(async_update_data, 'last_using_external_wattmeter') or \
                   async_update_data.last_using_external_wattmeter is not False:
                    _LOGGER.info("Using internal wattmeter registers for phase data")
                    async_update_data.last_using_external_wattmeter = False
                
                # Use internal registers based on connector type
                if "A" in connectors_in_use and "B" in connectors_in_use:
                    # For dual-connector wallbox, we show phase data from connector A (left side)
                    power_registers = [REG_POWER_L1_A, REG_POWER_L2_A, REG_POWER_L3_A]
                    current_registers = [REG_CURRENT_L1_A, REG_CURRENT_L2_A, REG_CURRENT_L3_A]
                    voltage_registers = [REG_VOLTAGE_L1_A, REG_VOLTAGE_L2_A, REG_VOLTAGE_L3_A]
                    energy_registers = [REG_ENERGY_L1_A, REG_ENERGY_L2_A, REG_ENERGY_L3_A]
                else:
                    # For single-connector wallbox, use the B connector (right side)
                    power_registers = [REG_POWER_L1_B, REG_POWER_L2_B, REG_POWER_L3_B]
                    current_registers = [REG_CURRENT_L1_B, REG_CURRENT_L2_B, REG_CURRENT_L3_B]
                    voltage_registers = [REG_VOLTAGE_L1_B, REG_VOLTAGE_L2_B, REG_VOLTAGE_L3_B]
                    energy_registers = [REG_ENERGY_L1_B, REG_ENERGY_L2_B, REG_ENERGY_L3_B]
            
            # Read the phase data
            try:
                for phase_num in range(1, 4):
                    # Get the registers for this phase
                    power_reg = power_registers[phase_num-1]
                    current_reg = current_registers[phase_num-1]
                    voltage_reg = voltage_registers[phase_num-1]
                    energy_reg = energy_registers[phase_num-1]
                    
                    # Read power
                    power_val = await client.read_holding_registers(power_reg, 1)
                    if power_val is not None:
                        key = f"power_l{phase_num}"
                        if data.get("external_wattmeter_present", False):
                            # For external wattmeter on single-connector, only store in B
                            if num_connectors == 1:
                                data["connector_B"][key] = power_val[0]
                            else:
                                # Store in both connector data structures since it's an external meter
                                data["connector_A"][key] = power_val[0]
                                data["connector_B"][key] = power_val[0]
                        elif "A" in connectors_in_use and "B" in connectors_in_use:
                            # For dual connector, store in appropriate connector
                            if power_reg in [REG_POWER_L1_A, REG_POWER_L2_A, REG_POWER_L3_A]:
                                data["connector_A"][key] = power_val[0]
                            else:
                                data["connector_B"][key] = power_val[0]
                        else:
                            # For single connector, store in connector B
                            data["connector_B"][key] = power_val[0]
                        
                        _LOGGER.debug("Read power for phase %s: %s W (raw: 0x%04X)", 
                                    phase_num, power_val[0], power_val[0])
                    
                    # Read current
                    current_val = await client.read_holding_registers(current_reg, 1)
                    if current_val is not None:
                        key = f"current_l{phase_num}"
                        if data.get("external_wattmeter_present", False):
                            # For external wattmeter on single-connector, only store in B
                            if num_connectors == 1:
                                data["connector_B"][key] = current_val[0]
                            else:
                                # Store in both connector data structures since it's an external meter
                                data["connector_A"][key] = current_val[0]
                                data["connector_B"][key] = current_val[0]
                        elif "A" in connectors_in_use and "B" in connectors_in_use:
                            # For dual connector, store in appropriate connector
                            if current_reg in [REG_CURRENT_L1_A, REG_CURRENT_L2_A, REG_CURRENT_L3_A]:
                                data["connector_A"][key] = current_val[0]
                            else:
                                data["connector_B"][key] = current_val[0]
                        else:
                            # For single connector, store in connector B
                            data["connector_B"][key] = current_val[0]
                            
                        _LOGGER.debug("Read current for phase %s: %s mA (raw: 0x%04X)", 
                                    phase_num, current_val[0], current_val[0])
                    
                    # Read voltage
                    voltage_val = await client.read_holding_registers(voltage_reg, 1)
                    if voltage_val is not None:
                        key = f"voltage_l{phase_num}"
                        if data.get("external_wattmeter_present", False):
                            # For external wattmeter on single-connector, only store in B
                            if num_connectors == 1:
                                data["connector_B"][key] = voltage_val[0]
                            else:
                                # Store in both connector data structures since it's an external meter
                                data["connector_A"][key] = voltage_val[0]
                                data["connector_B"][key] = voltage_val[0]
                        elif "A" in connectors_in_use and "B" in connectors_in_use:
                            # For dual connector, store in appropriate connector
                            if voltage_reg in [REG_VOLTAGE_L1_A, REG_VOLTAGE_L2_A, REG_VOLTAGE_L3_A]:
                                data["connector_A"][key] = voltage_val[0]
                            else:
                                data["connector_B"][key] = voltage_val[0]
                        else:
                            # For single connector, store in connector B
                            data["connector_B"][key] = voltage_val[0]
                            
                        _LOGGER.debug("Read voltage for phase %s: %s (0.1V) (raw: 0x%04X)", 
                                    phase_num, voltage_val[0], voltage_val[0])
                    
                    # Read energy
                    energy_val = await client.read_holding_registers(energy_reg, 2)  # Read as 32-bit
                    if energy_val is not None and len(energy_val) >= 2:
                        energy_val_32bit = ((energy_val[1] & 0xFFFF) << 16) | (energy_val[0] & 0xFFFF)
                        key = f"energy_l{phase_num}"
                        if data.get("external_wattmeter_present", False):
                            # For external wattmeter on single-connector, only store in B
                            if num_connectors == 1:
                                data["connector_B"][key] = energy_val_32bit
                            else:
                                # Store in both connector data structures since it's an external meter
                                data["connector_A"][key] = energy_val_32bit
                                data["connector_B"][key] = energy_val_32bit
                        elif "A" in connectors_in_use and "B" in connectors_in_use:
                            # For dual connector, store in appropriate connector
                            if energy_reg in [REG_ENERGY_L1_A, REG_ENERGY_L2_A, REG_ENERGY_L3_A]:
                                data["connector_A"][key] = energy_val_32bit
                            else:
                                data["connector_B"][key] = energy_val_32bit
                        else:
                            # For single connector, store in connector B
                            data["connector_B"][key] = energy_val_32bit
                            
                        _LOGGER.debug("Read energy for phase %s: %s mWh (raw: [0x%04X, 0x%04X], combined: 0x%08X)", 
                                    phase_num, energy_val_32bit, energy_val[0], energy_val[1], energy_val_32bit)
            except Exception as ex:
                _LOGGER.error("Error reading phase data: %s", ex)
                
            # Also read total energy from external wattmeter if available
            if data.get("external_wattmeter_present", False):
                try:
                    # Read total energy
                    total_energy = await client.read_holding_registers(REG_EXT_ENERGY_TOTAL, 2)  # Read as 32-bit
                    if total_energy is not None and len(total_energy) >= 2:
                        total_energy_32bit = ((total_energy[1] & 0xFFFF) << 16) | (total_energy[0] & 0xFFFF)
                        # For external wattmeter on single-connector, only store in B
                        if num_connectors == 1:
                            data["connector_B"]["total_energy_ext"] = total_energy_32bit
                        else:
                            # Store in both connector data structures since it's an external meter
                            data["connector_A"]["total_energy_ext"] = total_energy_32bit
                            data["connector_B"]["total_energy_ext"] = total_energy_32bit
                        _LOGGER.debug("Read total energy from external wattmeter: %s mWh", total_energy_32bit)
                        
                    # Read saved energy
                    saved_energy = await client.read_holding_registers(REG_EXT_ENERGY_SAVED_FLASH, 2)  # Read as 32-bit
                    if saved_energy is not None and len(saved_energy) >= 2:
                        saved_energy_32bit = ((saved_energy[1] & 0xFFFF) << 16) | (saved_energy[0] & 0xFFFF)
                        # For external wattmeter on single-connector, only store in B
                        if num_connectors == 1:
                            data["connector_B"]["saved_energy_ext"] = saved_energy_32bit
                        else:
                            # Store in both connector data structures since it's an external meter
                            data["connector_A"]["saved_energy_ext"] = saved_energy_32bit
                            data["connector_B"]["saved_energy_ext"] = saved_energy_32bit
                        _LOGGER.debug("Read saved energy from external wattmeter: %s mWh", saved_energy_32bit)
                        
                    # Read total power
                    total_power = await client.read_holding_registers(REG_EXT_POWER_SUM, 1)
                    if total_power is not None:
                        # For external wattmeter on single-connector, only store in B
                        if num_connectors == 1:
                            data["connector_B"]["power_sum"] = total_power[0]
                        else:
                            # Store in both connector data structures since it's an external meter
                            data["connector_A"]["power_sum"] = total_power[0]
                            data["connector_B"]["power_sum"] = total_power[0]
                        _LOGGER.debug("Read total power from external wattmeter: %s W", total_power[0])
                except Exception as ex:
                    _LOGGER.error("Error reading additional data from external wattmeter: %s", ex)
            
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
    try:
        await coordinator.async_refresh()
    except Exception as ex:
        _LOGGER.warning("Error during initial refresh: %s", ex)
        # Don't store coordinator on error to prevent memory leak
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {ex}") from ex

    # Store the coordinator in the hass data
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    entities = []
    
    # Create entity for each connector
    connector_mapping = {1: "A", 2: "B"}  # Map from index to letter
    for connector_idx in range(1, num_connectors + 1):
        connector_letter = connector_mapping[connector_idx]
        
        # For single-connector wallboxes, we always use connector_B data
        if num_connectors == 1:
            connector_key = "connector_B"
        else:
            connector_key = f"connector_{connector_letter}"
            
        connector_name = f"{name}" if num_connectors == 1 else f"{name} Connector {connector_letter}"
        
        # Add a suffix to the device_unique_id if we have multiple connectors
        connector_unique_id = device_unique_id if num_connectors == 1 else f"{device_unique_id}_connector_{connector_letter}"
        
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
                f"{connector_unique_id}_charge_power",
                connector_idx
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
        

    
    # Add the entities to Home Assistant
    async_add_entities(entities)

class OlifeWallboxSensor(CoordinatorEntity, SensorEntity):
    """Base class for Olife Energy Wallbox sensors using DataUpdateCoordinator."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._device_info = device_info
        self._device_unique_id = device_unique_id
        self._attr_has_entity_name = True
        self._attr_should_poll = False  # Coordinator handles updates
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        # Phase sensors should be available whether using external or internal wattmeter
        # We no longer require an external wattmeter for phase sensors to be available
        
        # Handle nested keys (e.g., "connector_A.wallbox_ev_state")
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
            
        # Handle nested keys (e.g., "connector_A.wallbox_ev_state")
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
    """Sensor for EV charging state.
    
    Reports the current state of the EV charging process (e.g., connected,
    charging, completed) using standardized Wallbox EV state codes.
    """

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._error_count = 0
        self._attr_entity_category = None  # Keep on main screen
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return "EV State"

    @property
    def native_value(self):
        """Return the state of the sensor (human-readable text)."""
        # Get the raw state
        raw_state = self._get_value_from_data()
        
        if raw_state is None:
            return None
            
        # Convert state to human-readable text
        if raw_state in WALLBOX_EV_STATES:
            return WALLBOX_EV_STATES[raw_state]
        else:
            if self._should_log_error():
                _LOGGER.warning("Unknown EV state: %s", raw_state)
            return f"Unknown ({raw_state})"
            
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        raw_state = self._get_value_from_data()
        if raw_state is None:
            return {}
            
        attributes = {
            "raw_state": raw_state,
            "state_code": raw_state,
        }
        
        # Add detailed description if available
        if raw_state in WALLBOX_EV_STATE_DESCRIPTIONS:
            attributes["description"] = WALLBOX_EV_STATE_DESCRIPTIONS[raw_state]
            
        return attributes
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the EV state."""
        raw_state = self._get_value_from_data()
        if not self.available or raw_state is None:
            return "mdi:ev-station-off"
            
        return WALLBOX_EV_STATE_ICONS.get(
            raw_state, 
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

class OlifeWallboxChargeCurrentSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox charge current."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Current"
        
    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # Main display
        
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
    """Sensor for total charge energy delivered.
    
    Reports cumulative energy delivered by the wallbox in kWh.
    Energy is stored as mWh on the device and converted for display.
    """

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Energy"
        
    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # Main display
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        val = self._get_value_from_data()
        if val is not None:
            return round(val / 1000.0, 2)
        return None
    
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

class OlifeWallboxChargePowerSensor(OlifeWallboxSensor):
    """Sensor for current charging power.
    
    Reports instantaneous power draw during charging in watts (W).
    """
    
    def __init__(self, coordinator, name, key, device_info, device_unique_id, connector_idx=None):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        # Store connector_idx if needed for future use
        self._connector_idx = connector_idx
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return "Charge Power"
        
    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # Main display
        
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
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:flash"



class OlifeWallboxCPStateSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox CP state."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._raw_state = None
        self._error_count = 0
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Diagnostic sensor
        
    def _should_log_error(self):
        """Determine whether to log an error based on error count."""
        return self._error_count == 1 or self._error_count % ERROR_LOG_THRESHOLD == 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return "CP State"

    @property
    def native_value(self):
        """Return the state of the sensor (human-readable text)."""
        # Get the raw state
        raw_state = self._get_value_from_data()
        
        if raw_state is None:
            return None
            
        # Convert state to human-readable text
        if raw_state in CP_STATES:
            return CP_STATES[raw_state]
        else:
            if self._should_log_error():
                _LOGGER.warning("Unknown CP state: %s", raw_state)
            return f"Unknown ({raw_state})"
            
    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        raw_state = self._get_value_from_data()
        if raw_state is None:
            return {}
            
        attributes = {
            "raw_state": raw_state,
            "state_code": raw_state,
        }
        
        # Add detailed description if available
        if raw_state in CP_STATE_DESCRIPTIONS:
            attributes["description"] = CP_STATE_DESCRIPTIONS[raw_state]
            
        return attributes
        
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the CP state."""
        raw_state = self._get_value_from_data()
        if not self.available or raw_state is None:
            return "mdi:help-circle-outline"
            
        return CP_STATE_ICONS.get(
            raw_state, 
            "mdi:help-circle-outline"
        )
        
    @property
    def state_class(self):
        """Return the state class."""
        return None

class OlifeWallboxErrorCodeSensor(OlifeWallboxSensor):
    """Sensor for Olife Energy Wallbox error codes."""

    def __init__(self, coordinator, name, key, device_info, device_unique_id):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to diagnostic tab
        
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
    """Sensor for per-phase power consumption.
    
    Reports power draw for individual electrical phases (L1, L2, L3).
    Useful for monitoring load balance across phases.
    """

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to diagnostic tab
    
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
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.POWER
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
        
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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to diagnostic tab
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Current"
        
    @property
    def native_value(self):
        """Return the phase current in Amperes."""
        if not self.available:
            return None
            
        # Current is reported in mA, convert to A
        current_ma = self._get_value_from_data()
        if current_ma is not None:
            return current_ma / 1000.0
        return None
    
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
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to diagnostic tab
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Voltage"
        
    @property
    def native_value(self):
        """Return the phase voltage in Volts."""
        if not self.available:
            return None
            
        # Voltage is reported in decivolts, convert to V
        voltage_dv = self._get_value_from_data()
        if voltage_dv is not None:
            return voltage_dv / 10.0
        return None
    
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "V"
    
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.VOLTAGE
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:sine-wave"

class OlifeWallboxPhaseEnergySensor(OlifeWallboxSensor):
    """Sensor for per-phase energy consumption.
    
    Reports cumulative energy delivered per electrical phase in kWh.
    Energy stored as mWh on device, converted for display.
    """

    def __init__(self, coordinator, name, key, device_info, device_unique_id, phase_num):
        """Initialize the sensor."""
        super().__init__(coordinator, name, key, device_info, device_unique_id)
        self._phase_num = phase_num
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to diagnostic tab 
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Phase {self._phase_num} Energy"
        
    @property
    def native_value(self):
        """Return the phase energy in kWh."""
        if not self.available:
            return None
            
        # Energy is reported in mWh, convert to kWh (divide by 1,000,000)
        energy_mwh = self._get_value_from_data()
        if energy_mwh is not None:
            return round(energy_mwh / 1000000.0, 2)
        return None
    
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
        
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lightning-bolt" 