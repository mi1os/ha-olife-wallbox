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
    DEFAULT_READ_ONLY
)
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Olife Energy Wallbox from a config entry."""
    try:
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = entry.data

        # Determine which platforms to load based on read-only setting
        read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
        
        if read_only:
            # In read-only mode, only include sensor platform
            platforms_to_setup = ["sensor"]
            _LOGGER.info("Olife Wallbox integration set up in read-only mode")
        else:
            # Normal mode - include all platforms
            platforms_to_setup = PLATFORMS
        
        # Set up selected platforms for this device/entry
        await hass.config_entries.async_forward_entry_setups(entry, platforms_to_setup)
        
        # Set up services (only if not in read-only mode)
        if not read_only:
            await async_setup_services(hass)
        
        # Register update listener for config entry changes
        entry.async_on_unload(entry.add_update_listener(async_options_updated))

        return True
    except Exception as ex:
        _LOGGER.error("Error setting up Olife Wallbox integration: %s", ex)
        raise ConfigEntryNotReady(f"Failed to set up Olife Wallbox integration: {ex}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Determine which platforms were loaded based on read-only setting
    read_only = entry.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    platforms_to_unload = ["sensor"] if read_only else PLATFORMS
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms_to_unload)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # If this is the last entry, unload the services
        if not hass.data[DOMAIN]:
            async_unload_services(hass)

    return unload_ok

async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading Olife Wallbox integration")
    await hass.config_entries.async_reload(entry.entry_id) 