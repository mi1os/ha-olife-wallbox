"""Services for Olife Energy Wallbox integration."""
import logging
import re
from typing import Any, Dict, List, Optional, Set

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    REG_CHARGING_ENABLE_A,
    REG_CHARGING_ENABLE_B,
    REG_CURRENT_LIMIT_A,
    REG_CURRENT_LIMIT_B,
    REG_CLOUD_CURRENT_LIMIT_A,
    REG_CLOUD_CURRENT_LIMIT_B,
    REG_MAX_STATION_CURRENT,
    REG_LED_PWM,
)
from .modbus_client import OlifeWallboxModbusClient

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_START_CHARGE = "start_charge"
SERVICE_STOP_CHARGE = "stop_charge"
SERVICE_SET_CURRENT_LIMIT = "set_current_limit"
SERVICE_SET_MAX_CURRENT = "set_max_current" 
SERVICE_SET_LED_BRIGHTNESS = "set_led_brightness"
SERVICE_RESET_ENERGY_COUNTERS = "reset_energy_counters"
SERVICE_RELOAD_INTEGRATION = "reload"

# Service schemas
WALLBOX_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)

CURRENT_LIMIT_SCHEMA = WALLBOX_SERVICE_SCHEMA.extend(
    {
        vol.Required("current_limit"): vol.All(vol.Coerce(int), vol.Range(min=0, max=32)),
    }
)

MAX_CURRENT_SCHEMA = WALLBOX_SERVICE_SCHEMA.extend(
    {
        vol.Required("max_current"): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
    }
)

LED_BRIGHTNESS_SCHEMA = WALLBOX_SERVICE_SCHEMA.extend(
    {
        vol.Required("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=1000)),
    }
)

RESET_COUNTERS_SCHEMA = WALLBOX_SERVICE_SCHEMA.extend(
    {
        vol.Optional("daily", default=True): cv.boolean,
        vol.Optional("monthly", default=True): cv.boolean,
        vol.Optional("yearly", default=True): cv.boolean,
    }
)

async def _get_client_for_device(hass: HomeAssistant, device_id: str) -> OlifeWallboxModbusClient:
    """Get the ModbusClient for a device ID."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    
    device = device_registry.async_get(device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")
        
    if not device.identifiers:
        raise ValueError(f"Device {device_id} has no identifiers")
        
    # Find the entry_id from the device's identifiers
    domain_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            domain_id = identifier[1]
            break
            
    if not domain_id:
        raise ValueError(f"Device {device_id} not associated with {DOMAIN}")
        
    # Split domain_id to get connection details
    try:
        host, port, slave_id = domain_id.split("_")
        port = int(port)
        slave_id = int(slave_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid device identifier format: {domain_id}")
        
    client = OlifeWallboxModbusClient(host, port, slave_id)
    return client

async def _set_charging_state(hass: HomeAssistant, device_id: str, enable: bool) -> None:
    """Set the charging state of a wallbox."""
    try:
        client = await _get_client_for_device(hass, device_id)
        value = 1 if enable else 0
        if await client.write_register(REG_CHARGING_ENABLE_A if enable else REG_CHARGING_ENABLE_B, value):
            action = "enabled" if enable else "disabled"
            _LOGGER.info("Charging %s for device %s", action, device_id)
            
            # Update switch state immediately for better responsiveness
            entity_registry = er.async_get(hass)
            for entity_id in entity_registry.entities.values():
                if (
                    entity_id.domain == "switch"
                    and entity_id.unique_id
                    and device_id in entity_id.unique_id
                    and "charging_switch" in entity_id.unique_id
                ):
                    # Force entity state updates for better responsiveness
                    entity = entity_registry.async_get_entity_id(
                        "switch", DOMAIN, entity_id.unique_id
                    )
                    if entity and hass.states.get(entity):
                        await hass.services.async_call(
                            "homeassistant", "update_entity", {"entity_id": entity}
                        )
                    break
        else:
            action = "enable" if enable else "disable"
            _LOGGER.error("Failed to %s charging for device %s", action, device_id)
    except Exception as ex:
        _LOGGER.error("Error setting charging state: %s", ex)
        raise

async def _set_current_limit(hass: HomeAssistant, device_id: str, current_limit: int) -> None:
    """Set the current limit of a wallbox."""
    try:
        client = await _get_client_for_device(hass, device_id)
        # Use cloud registers for setting current limit (not read-only)
        # REG_CURRENT_LIMIT_A/B are read-only, use REG_CLOUD_CURRENT_LIMIT_A/B instead
        if await client.write_register(REG_CLOUD_CURRENT_LIMIT_B, current_limit):
            _LOGGER.info("Current limit set to %s A for device %s", current_limit, device_id)
            
            # Update number state for better responsiveness
            entity_registry = er.async_get(hass)
            for entity_id in entity_registry.entities.values():
                if (
                    entity_id.domain == "number"
                    and entity_id.unique_id
                    and device_id in entity_id.unique_id
                    and "current_limit" in entity_id.unique_id
                ):
                    entity = entity_registry.async_get_entity_id(
                        "number", DOMAIN, entity_id.unique_id
                    )
                    if entity and hass.states.get(entity):
                        await hass.services.async_call(
                            "homeassistant", "update_entity", {"entity_id": entity}
                        )
                    break
        else:
            _LOGGER.error("Failed to set current limit for device %s", device_id)
    except Exception as ex:
        _LOGGER.error("Error setting current limit: %s", ex)
        raise

async def _set_max_current(hass: HomeAssistant, device_id: str, max_current: int) -> None:
    """
    This service is deprecated. 
    The PP current limit is read-only and determined by the charging cable.
    """
    _LOGGER.warning("The set_max_current service is deprecated as the PP current limit is read-only")
    raise HomeAssistantError("The PP current limit is read-only and determined by the charging cable")

async def _set_led_brightness(hass: HomeAssistant, device_id: str, brightness: int) -> None:
    """Set the LED brightness of a wallbox."""
    try:
        client = await _get_client_for_device(hass, device_id)
        if await client.write_register(REG_LED_PWM, brightness):
            _LOGGER.info("LED brightness set to %s for device %s", brightness, device_id)
            
            # Update number state for better responsiveness
            entity_registry = er.async_get(hass)
            for entity_id in entity_registry.entities.values():
                if (
                    entity_id.domain == "number"
                    and entity_id.unique_id
                    and device_id in entity_id.unique_id
                    and "led_pwm" in entity_id.unique_id
                ):
                    entity = entity_registry.async_get_entity_id(
                        "number", DOMAIN, entity_id.unique_id
                    )
                    if entity and hass.states.get(entity):
                        await hass.services.async_call(
                            "homeassistant", "update_entity", {"entity_id": entity}
                        )
                    break
        else:
            _LOGGER.error("Failed to set LED brightness for device %s", device_id)
    except Exception as ex:
        _LOGGER.error("Error setting LED brightness: %s", ex)
        raise

async def _reset_energy_counters(hass: HomeAssistant, device_id: str, 
                                daily: bool = True, monthly: bool = True, yearly: bool = True) -> None:
    """Reset energy counters."""
    entity_registry = er.async_get(hass)
    types_to_reset = []
    if daily:
        types_to_reset.append("daily")
    if monthly:
        types_to_reset.append("monthly")
    if yearly:
        types_to_reset.append("yearly")
        
    if not types_to_reset:
        _LOGGER.warning("No counter types specified for reset")
        return
        
    _LOGGER.info("Resetting %s energy counters for device %s", ", ".join(types_to_reset), device_id)
        
    # Find the energy counter entities for this device
    for entity_id in entity_registry.entities.values():
        if (
            entity_id.domain == "sensor"
            and entity_id.unique_id
            and device_id in entity_id.unique_id
        ):
            reset_this = False
            for type_name in types_to_reset:
                if f"{type_name}_charge_energy" in entity_id.unique_id:
                    reset_this = True
                    break
                    
            if reset_this:
                entity = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, entity_id.unique_id
                )
                if entity:
                    # Add event to the event bus to reset the counter
                    hass.bus.async_fire(f"{DOMAIN}_reset_counter", {
                        "entity_id": entity,
                        "device_id": device_id,
                        "timestamp": dt_util.utcnow().isoformat()
                    })
                    _LOGGER.info("Reset event sent for %s", entity)

async def _reload_integration(hass: HomeAssistant, device_id: str = None) -> None:
    """Attempt to reload the integration entities without a full restart.
    
    This will disconnect and reconnect to the device, and refresh all entities.
    Note: This can't replace a full restart for code changes, but may help refresh the integration state.
    """
    _LOGGER.info("Attempting to reload Olife Wallbox integration")
    
    # Get relevant entries
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device:
            # Get the config entry for this device
            config_entries = [
                entry_id for entry_id in device.config_entries 
                if entry_id in hass.config_entries.async_entries(DOMAIN)
            ]
        else:
            _LOGGER.error(f"Device with ID {device_id} not found")
            return
    else:
        # Reload all entries for this domain
        config_entries = [
            entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)
        ]
    
    # Force reload each entry
    success_count = 0
    for entry_id in config_entries:
        try:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry:
                # This won't reload code, but will reconnect to devices and refresh entities
                _LOGGER.debug(f"Reloading config entry {entry.title} ({entry_id})")
                await hass.config_entries.async_reload(entry_id)
                success_count += 1
        except Exception as ex:
            _LOGGER.error(f"Error reloading entry {entry_id}: {ex}")
    
    if success_count > 0:
        _LOGGER.info(f"Successfully reloaded {success_count} Olife Wallbox integration(s)")
    else:
        _LOGGER.warning("No Olife Wallbox integrations were reloaded")

async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Olife Wallbox."""
    
    async def handle_start_charge(call: ServiceCall) -> None:
        """Handle the start charge service call."""
        await _set_charging_state(hass, call.data["device_id"], True)
        
    async def handle_stop_charge(call: ServiceCall) -> None:
        """Handle the stop charge service call."""
        await _set_charging_state(hass, call.data["device_id"], False)
        
    async def handle_set_current_limit(call: ServiceCall) -> None:
        """Handle the set current limit service call."""
        await _set_current_limit(hass, call.data["device_id"], call.data["current_limit"])
        
    async def handle_set_max_current(call: ServiceCall) -> None:
        """Handle the set max current service call."""
        await _set_max_current(hass, call.data["device_id"], call.data["max_current"])
        
    async def handle_set_led_brightness(call: ServiceCall) -> None:
        """Handle the set LED brightness service call."""
        await _set_led_brightness(hass, call.data["device_id"], call.data["brightness"])
        
    async def handle_reset_energy_counters(call: ServiceCall) -> None:
        """Handle the reset energy counters service call."""
        await _reset_energy_counters(
            hass, 
            call.data["device_id"],
            call.data.get("daily", True),
            call.data.get("monthly", True),
            call.data.get("yearly", True)
        )
        
    async def handle_reload_integration(call: ServiceCall) -> None:
        """Handle the reload_integration service call."""
        if "device_id" in call.data:
            await _reload_integration(hass, call.data["device_id"])
        else:
            await _reload_integration(hass)
    
    hass.services.async_register(
        DOMAIN, SERVICE_START_CHARGE, handle_start_charge, schema=WALLBOX_SERVICE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_CHARGE, handle_stop_charge, schema=WALLBOX_SERVICE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_CURRENT_LIMIT, handle_set_current_limit, schema=CURRENT_LIMIT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_MAX_CURRENT, handle_set_max_current, schema=MAX_CURRENT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_LED_BRIGHTNESS, handle_set_led_brightness, schema=LED_BRIGHTNESS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_ENERGY_COUNTERS, handle_reset_energy_counters, schema=RESET_COUNTERS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RELOAD_INTEGRATION, handle_reload_integration, schema=vol.Schema({
            vol.Optional("device_id"): cv.string,
        })
    )

def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Olife Wallbox services."""
    for service in [
        SERVICE_START_CHARGE,
        SERVICE_STOP_CHARGE,
        SERVICE_SET_CURRENT_LIMIT,
        SERVICE_SET_MAX_CURRENT,
        SERVICE_SET_LED_BRIGHTNESS,
        SERVICE_RESET_ENERGY_COUNTERS,
        SERVICE_RELOAD_INTEGRATION,
    ]:
        hass.services.async_remove(DOMAIN, service) 