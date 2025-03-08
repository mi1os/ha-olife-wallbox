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
    REG_NUM_CONNECTORS
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
            
        # Serial number (10 registers)
        serial_chars = []
        serial_registers = await client.read_holding_registers(REG_SERIAL_NUMBER_START, 10)
        if serial_registers:
            for register in serial_registers:
                if register > 0:
                    # Convert 16-bit register to two ASCII characters
                    serial_chars.append(chr((register >> 8) & 0xFF))
                    serial_chars.append(chr(register & 0xFF))
            device_info["serial_number"] = ''.join(c for c in serial_chars if c.isprintable())
            
        # Model (3 registers)
        model_chars = []
        model_registers = await client.read_holding_registers(REG_MODEL_START, 3)
        if model_registers:
            for register in model_registers:
                if register > 0:
                    # Convert 16-bit register to two ASCII characters
                    model_chars.append(chr((register >> 8) & 0xFF))
                    model_chars.append(chr(register & 0xFF))
            device_info["model"] = ''.join(c for c in model_chars if c.isprintable())
            
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