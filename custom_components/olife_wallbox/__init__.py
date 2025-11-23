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
    try:
        # Get configuration from entry
        host = entry.data[CONF_HOST]
        port = int(entry.data.get(CONF_PORT, 502))
        slave_id = int(entry.data.get(CONF_SLAVE_ID, 1))
        name = entry.data.get(CONF_NAME, "Olife Wallbox")
        
        # Get options or defaults
        read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
        
        # Create a ModbusClient instance
        client = OlifeWallboxModbusClient(host, port, slave_id)
        if not await client.connect():
            await client.disconnect()
            _LOGGER.error("Failed to connect to Olife Wallbox at %s:%s", host, port)
            raise ConfigEntryNotReady("Failed to connect to device")
            
        # Update the device registry - since 2022.8, this is recommended even before platform setup
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            name=name,
            manufacturer="Olife Energy",
            model="Wallbox",
            # Use Wifi icon since there's no specific Wallbox icon
            suggested_area="Garage",
            identifiers={(DOMAIN, f"{host}_{port}_{slave_id}")},
            sw_version="unknown",  # Will be updated later
            hw_version="unknown",  # Will be updated later
        )
        
        # Read system and device information
        device_info = {}
        
        try:
            # Hardware and software version (these can help identify capabilities)
            hw_version = await client.read_holding_registers(REG_HW_VERSION, 1)
            sw_version = await client.read_holding_registers(REG_SW_VERSION, 1)
            
            # Number of connectors
            num_connectors = await client.read_holding_registers(REG_NUM_CONNECTORS, 1)
            
            # Serial number - two registers that need special handling
            sn_first = await client.read_holding_registers(REG_SN_FIRST_PART, 1)
            sn_last = await client.read_holding_registers(REG_SN_LAST_PART, 1)
            
            if hw_version is not None and len(hw_version) >= 1:
                hw_value = hw_version[0]
                hw_major = hw_value // 100
                hw_minor = hw_value % 100
                device_info["hw_version"] = f"{hw_major}.{hw_minor:02d}"
                
            if sw_version is not None and len(sw_version) >= 1:
                sw_value = sw_version[0]
                sw_major = sw_value // 100
                sw_minor = sw_value % 100
                device_info["sw_version"] = f"{sw_major}.{sw_minor:02d}"
                
            if num_connectors is not None and len(num_connectors) >= 1:
                device_info["num_connectors"] = num_connectors[0]
                
                # For single-connector wallboxes, we always use the B registers
                if num_connectors[0] == 1:
                    device_info["connectors_in_use"] = ["B"]
                else:
                    device_info["connectors_in_use"] = ["A", "B"]
                
            if sn_first is not None and sn_last is not None:
                if len(sn_first) >= 1 and len(sn_last) >= 1:
                    sn_first_val = sn_first[0]
                    sn_last_val = sn_last[0]
                    serial_number = f"{sn_first_val:03d}{sn_last_val:03d}"
                    device_info["serial_number"] = serial_number
                    
            # Update the device registry with the device information
            device_registry.async_update_device(
                device_id=device_registry.async_get_device(identifiers={(DOMAIN, f"{host}_{port}_{slave_id}")}).id,
                name=name,
                manufacturer="Olife Energy",
                model=f"Wallbox ({device_info.get('num_connectors', '?')}-connector)",
                sw_version=device_info.get("sw_version", "Unknown"),
                hw_version=device_info.get("hw_version", "Unknown"),
            )
            
        except Exception as ex:
            _LOGGER.warning("Failed to read device information: %s", ex)
            # Continue with default values if reading device info fails
        
        # Default data
        if "num_connectors" not in device_info:
            device_info["num_connectors"] = 1
            device_info["connectors_in_use"] = ["B"]
            
        if "sw_version" not in device_info:
            device_info["sw_version"] = "Unknown"
            
        if "hw_version" not in device_info:
            device_info["hw_version"] = "Unknown"
        
        # Store the client and device info for platform access
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "client": client,
            "device_info": device_info,
            "read_only": read_only,
        }
        
        # Register services once (on first setup)
        if len(hass.data[DOMAIN]) == 1:
            # Register services
            await async_setup_services(hass)
        
        # Register a listener for option updates
        entry.async_on_unload(entry.add_update_listener(async_options_updated))
        
        # Forward setup to platforms - use the recommended approach
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        return True
    except Exception as ex:
        _LOGGER.error("Failed to set up Olife Wallbox: %s", ex)
        # Only try to disconnect if client was created
        if 'client' in locals():
            await client.disconnect()
        return False

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