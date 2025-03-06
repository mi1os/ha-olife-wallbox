"""Diagnostics support for Olife Wallbox."""
from __future__ import annotations

from typing import Any
from datetime import datetime

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_SLAVE_ID, CONF_SCAN_INTERVAL

REDACT_CONFIG = {CONF_HOST}
TO_REDACT = [CONF_HOST, CONF_PASSWORD, "ip_address", "host"]

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    device_id = None
    
    # Get device info
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)
    
    # Find device for this entry
    device_entries = []
    for device in dr.async_entries_for_config_entry(device_reg, entry.entry_id):
        device_id = device.id
        device_info = {
            "id": device.id,
            "name": device.name,
            "model": device.model,
            "manufacturer": device.manufacturer,
            "sw_version": device.sw_version,
        }
        device_entries.append(device_info)
        
    # Get entities for this device
    entity_entries = []
    if device_id:
        for entity_entry in er.async_entries_for_device(entity_reg, device_id):
            entity_info = {
                "entity_id": entity_entry.entity_id,
                "name": entity_entry.name,
                "domain": entity_entry.domain,
                "platform": entity_entry.platform,
                "unique_id": entity_entry.unique_id,
                "original_name": entity_entry.original_name,
                "disabled": entity_entry.disabled,
            }
            entity_entries.append(entity_info)
    
    # Get device clients if possible
    try:
        device_id_parts = device_id.split("_")
        host, port, slave_id = data.get(CONF_HOST), data.get("port"), data.get(CONF_SLAVE_ID)
        
        # Attempt to create a Modbus client for diagnostics but don't connect
        from .modbus_client import OlifeWallboxModbusClient
        client = OlifeWallboxModbusClient(host, port, slave_id)
        
        client_info = {
            "connection_errors": client._connection_errors,
            "consecutive_errors": client._consecutive_errors,
            "last_connection_attempt": client._last_connect_attempt.isoformat() if client._last_connect_attempt != datetime.min else None,
            "last_successful_connection": client._last_successful_connection.isoformat() if client._last_successful_connection != datetime.min else None,
        }
    except (KeyError, IndexError, AttributeError, ImportError) as ex:
        client_info = {"error": str(ex)}
    
    diagnostics_data = {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "config_data": async_redact_data(dict(data), TO_REDACT),
        "device_info": device_entries,
        "entity_info": entity_entries,
        "client_info": client_info,
    }
    
    return diagnostics_data 