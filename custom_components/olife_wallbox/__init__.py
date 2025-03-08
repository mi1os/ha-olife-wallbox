"""The Olife Energy Wallbox integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN, 
    PLATFORMS,
    CONF_READ_ONLY,
    DEFAULT_READ_ONLY,
    REG_HW_VERSION,
    REG_SW_VERSION,
    REG_SERIAL_NUMBER_START,
    REG_MODEL_START,
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
        
        # Hardware version
        hw_version = await client.read_holding_registers(REG_HW_VERSION, 1)
        if hw_version:
            device_info["hw_version"] = f"{hw_version[0]/100:.2f}"
            
        # Software version
        sw_version = await client.read_holding_registers(REG_SW_VERSION, 1)
        if sw_version:
            device_info["sw_version"] = f"{sw_version[0]/100:.2f}"
            
        # Serial number (first and last parts)
        sn_first = await client.read_holding_registers(REG_SN_FIRST_PART, 1)
        sn_last = await client.read_holding_registers(REG_SN_LAST_PART, 1)
        if sn_first and sn_last:
            device_info["serial_number"] = f"{sn_first[0]:03d}-{sn_last[0]:03d}"
            
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
        if pn_type:
            station_type = pn_type[0] // 10  # First digit
            station_variant = pn_type[0] % 10  # Second digit
            
            station_types = {1: "WB", 2: "DB", 3: "ST"}
            station_variants = {1: "Base", 2: "Smart"}
            
            station_type_str = station_types.get(station_type, "Unknown")
            station_variant_str = station_variants.get(station_variant, "Unknown")
            
            device_info["model"] = f"{station_type_str} {station_variant_str}"
            
        # Connector information
        pn_left = await client.read_holding_registers(REG_PN_LEFT, 1)
        pn_right = await client.read_holding_registers(REG_PN_RIGHT, 1)
        
        connector_types = {1: "Yazaki", 2: "Mennekes"}
        cable_types = {1: "Socket", 2: "Coil Cable", 3: "Straight Cable"}
        
        if pn_left:
            left_type = pn_left[0] // 10  # First digit
            left_cable = pn_left[0] % 10  # Second digit
            left_type_str = connector_types.get(left_type, "Unknown")
            left_cable_str = cable_types.get(left_cable, "Unknown")
            device_info["connector_left"] = f"{left_type_str} {left_cable_str}"
            
        if pn_right:
            right_type = pn_right[0] // 10  # First digit
            right_cable = pn_right[0] % 10  # Second digit
            right_type_str = connector_types.get(right_type, "Unknown")
            right_cable_str = cable_types.get(right_cable, "Unknown")
            device_info["connector_right"] = f"{right_type_str} {right_cable_str}"
            
        # Number of connectors
        num_connectors = await client.read_holding_registers(REG_NUM_CONNECTORS, 1)
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