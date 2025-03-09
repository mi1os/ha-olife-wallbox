"""The Olife Energy Wallbox integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN, 
    PLATFORMS,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    CONF_SLAVE_ID,
    REG_HW_VERSION,
    REG_SW_VERSION,
    REG_NUM_CONNECTORS,
    REG_SN_FIRST_PART,
    REG_SN_LAST_PART,
    REG_YEAR_MONTH,
    REG_DAY_HOUR,
    REG_PN_TYPE,
    REG_PN_LEFT,
    REG_PN_RIGHT
)
from .services import async_setup_services, async_unload_services
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Olife Energy Wallbox from a config entry."""
    # Get configuration
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 502)
    slave_id = entry.data.get("slave_id", 1)
    
    # Get options with defaults
    read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize Modbus client
    client = OlifeWallboxModbusClient(host, port, slave_id)
    
    # Connect and fetch device info
    try:
        # Attempt to connect and read device information
        if not await client.connect():
            raise ConfigEntryNotReady(f"Failed to connect to Olife Wallbox at {host}:{port}")
            
        # Read device information
        device_info = {}
        
        # Hardware and software versions
        hw_version = await client.read_holding_registers(REG_HW_VERSION, 1)
        sw_version = await client.read_holding_registers(REG_SW_VERSION, 1)
        
        _LOGGER.debug("Raw HW_VERSION register value: %s", hw_version)
        _LOGGER.debug("Raw SW_VERSION register value: %s", sw_version)
        
        if hw_version:
            device_info["hw_version"] = f"{hw_version[0]/100:.2f}"
            _LOGGER.info("Hardware version: %s", device_info["hw_version"])
        else:
            _LOGGER.warning("Could not read hardware version from register %s", REG_HW_VERSION)
            
        if sw_version:
            device_info["sw_version"] = f"{sw_version[0]/100:.2f}"
            _LOGGER.info("Software version: %s", device_info["sw_version"])
        else:
            _LOGGER.warning("Could not read software version from register %s", REG_SW_VERSION)
            
        # Serial number
        sn_first = await client.read_holding_registers(REG_SN_FIRST_PART, 1)
        sn_last = await client.read_holding_registers(REG_SN_LAST_PART, 1)
        
        _LOGGER.debug("Raw SN_FIRST_PART register value: %s", sn_first)
        _LOGGER.debug("Raw SN_LAST_PART register value: %s", sn_last)
        
        if sn_first and sn_last:
            device_info["serial_number"] = f"{sn_first[0]:03d}-{sn_last[0]:03d}"
            _LOGGER.info("Serial number: %s", device_info["serial_number"])
        else:
            _LOGGER.warning("Could not read serial number from registers %s and %s", 
                           REG_SN_FIRST_PART, REG_SN_LAST_PART)
            
        # Manufacturing date
        year_month = await client.read_holding_registers(REG_YEAR_MONTH, 1)
        day_hour = await client.read_holding_registers(REG_DAY_HOUR, 1)
        if year_month and day_hour:
            year = 2000 + ((year_month[0] // 100) % 100)  # Extract YY from YYMM
            month = year_month[0] % 100                   # Extract MM from YYMM
            day = day_hour[0] // 100                      # Extract DD from DDHH
            hour = day_hour[0] % 100                      # Extract HH from DDHH
            device_info["manufactured"] = f"{year}-{month:02d}-{day:02d} {hour:02d}:00"
            
        # Station type
        pn_type = await client.read_holding_registers(REG_PN_TYPE, 1)
        _LOGGER.debug("Raw PN_TYPE register value: %s", pn_type)
        if pn_type and pn_type[0] < 100:  # Sanity check for valid values
            station_type = pn_type[0] // 10  # First digit
            station_variant = pn_type[0] % 10  # Second digit
            
            _LOGGER.info("Decoded station type: type=%s, variant=%s", station_type, station_variant)
            
            station_types = {
                1: "WB (Wallbox)",
                2: "DB (DoubleBox)",
                3: "ST (Station)"
            }
            station_variants = {1: "Base", 2: "Smart"}
            
            station_type_str = station_types.get(station_type, "Unknown")
            station_variant_str = station_variants.get(station_variant, "Unknown")
            
            device_info["model"] = f"{station_type_str} {station_variant_str}"
            _LOGGER.info("Set model to: %s", device_info["model"])
        else:
            # Handle invalid or missing model information
            _LOGGER.info("Invalid or missing station type value: %s", pn_type)
            device_info["model"] = "Olife Wallbox"  # Use a generic model name instead of Unknown Unknown
            
        # Connector information
        pn_left = await client.read_holding_registers(REG_PN_LEFT, 1)
        pn_right = await client.read_holding_registers(REG_PN_RIGHT, 1)
        
        _LOGGER.debug("Raw PN_LEFT register value: %s", pn_left)
        _LOGGER.debug("Raw PN_RIGHT register value: %s", pn_right)
        
        connector_types = {1: "Yazaki", 2: "Mennekes"}
        cable_types = {1: "Socket", 2: "Coil Cable", 3: "Straight Cable"}
        
        if pn_left and pn_left[0] < 100:  # Sanity check for valid values
            left_type = pn_left[0] // 10  # First digit
            left_cable = pn_left[0] % 10  # Second digit
            _LOGGER.info("Decoded left connector: type=%s, cable=%s", left_type, left_cable)
            left_type_str = connector_types.get(left_type, "Unknown")
            left_cable_str = cable_types.get(left_cable, "Unknown")
            device_info["connector_left"] = f"{left_type_str} {left_cable_str}"
            _LOGGER.info("Set connector_left to: %s", device_info["connector_left"])
        else:
            # Handle invalid or missing connector information
            _LOGGER.info("Invalid or missing left connector value: %s", pn_left)
            device_info["connector_left"] = "Type 2"  # Default to most common type
            
        if pn_right and pn_right[0] < 100:  # Sanity check for valid values
            right_type = pn_right[0] // 10  # First digit
            right_cable = pn_right[0] % 10  # Second digit
            _LOGGER.info("Decoded right connector: type=%s, cable=%s", right_type, right_cable)
            right_type_str = connector_types.get(right_type, "Unknown")
            right_cable_str = cable_types.get(right_cable, "Unknown")
            device_info["connector_right"] = f"{right_type_str} {right_cable_str}"
            _LOGGER.info("Set connector_right to: %s", device_info["connector_right"])
        else:
            # Handle invalid or missing connector information
            _LOGGER.info("Invalid or missing right connector value: %s", pn_right)
            device_info["connector_right"] = "Type 2"  # Default to most common type
            
        # Number of connectors
        num_connectors = await client.read_holding_registers(REG_NUM_CONNECTORS, 1)
        _LOGGER.debug("Raw NUM_CONNECTORS register value: %s", num_connectors)
        if num_connectors:
            device_info["num_connectors"] = num_connectors[0]
            _LOGGER.info("Device has %s connector(s)", num_connectors[0])
        else:
            # Default to 1 connector if we can't read this register
            device_info["num_connectors"] = 1
            _LOGGER.warning("Could not determine number of connectors, assuming 1")
        
        # Store device info in hass.data
        hass.data[DOMAIN][entry.entry_id] = {
            "client": client,
            "device_info": device_info
        }
        
        # Log device information
        _LOGGER.info(
            "Connected to Olife Wallbox: Model=%s, HW=%s, SW=%s, S/N=%s, Connectors=%s",
            device_info.get("model", "Unknown"),
            device_info.get("hw_version", "Unknown"),
            device_info.get("sw_version", "Unknown"),
            device_info.get("serial_number", "Unknown"),
            device_info.get("num_connectors", 1)
        )
        
        # Create enhanced device info with all the information we collected
        device_registry = dr.async_get(hass)
        
        # Create a unique ID for the device
        device_unique_id = f"{host}_{port}_{slave_id}"
        
        # Create a more detailed model name that includes connector information
        model_info = device_info.get("model", "Olife Wallbox")
        
        # If model info contains "Unknown", replace with a more generic term
        if "Unknown Unknown" in model_info:
            model_info = "Olife Wallbox"
        
        connector_info = []
        
        if "connector_left" in device_info:
            connector_left = device_info["connector_left"]
            # Only add connector info if it's not Unknown Unknown
            if connector_left and "Unknown Unknown" not in connector_left:
                connector_info.append(f"Left: {connector_left}")
            elif device_info.get("num_connectors", 1) > 0:
                connector_info.append("Left: Type 2")
        
        if "connector_right" in device_info:
            connector_right = device_info["connector_right"]
            # Only add connector info if it's not Unknown Unknown
            if connector_right and "Unknown Unknown" not in connector_right:
                connector_info.append(f"Right: {connector_right}")
            elif device_info.get("num_connectors", 1) > 0:
                connector_info.append("Right: Type 2")
        
        if connector_info:
            detailed_model = f"{model_info} ({', '.join(connector_info)})"
        else:
            detailed_model = model_info
        
        # Log the complete device info for debugging
        _LOGGER.info("Complete device info: %s", device_info)
        _LOGGER.info("Using detailed model description: %s", detailed_model)
        
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_unique_id)},
            name=entry.data.get(CONF_NAME, "Olife Wallbox"),
            manufacturer="Olife Energy",
            model=detailed_model,
            sw_version=device_info.get("sw_version", "Unknown"),
            hw_version=device_info.get("hw_version", "Unknown"),
            suggested_area="Garage",
        )
        
        # Determine which platforms to load based on read-only setting
        if read_only:
            _LOGGER.info("Read-only mode enabled, only loading sensor platform")
            platforms_to_load = ["sensor"]
        else:
            _LOGGER.info("Loading all control platforms")
            platforms_to_load = PLATFORMS
        
        # Set up services
        await async_setup_services(hass)
        
        # Register a listener for option updates
        entry.async_on_unload(entry.add_update_listener(async_options_updated))
        
        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, platforms_to_load)
        
        return True
    except Exception as ex:
        _LOGGER.error("Failed to set up Olife Wallbox: %s", ex)
        await client.disconnect()
        raise ConfigEntryNotReady(f"Error setting up Olife Wallbox: {ex}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Get options to determine which platforms were loaded
    read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    platforms_to_unload = ["sensor"] if read_only else PLATFORMS
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms_to_unload)
    
    # Disconnect client
    if unload_ok and hass.data[DOMAIN].get(entry.entry_id):
        client = hass.data[DOMAIN][entry.entry_id].get("client")
        if client:
            await client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    # Unload services if this is the last entry
    if not hass.data[DOMAIN]:
        async_unload_services(hass)
    
    return unload_ok

async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading entry")
    await hass.config_entries.async_reload(entry.entry_id) 