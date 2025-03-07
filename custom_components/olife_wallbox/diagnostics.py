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
    data = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), REDACT_CONFIG),
            "options": dict(entry.options),
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "source": str(entry.source),
            "version": entry.version,
        },
        "statistics": {
            "connection": {},
            "entities": {},
            "modbus": {}
        }
    }

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Get device diagnostics
    data["devices"] = []
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        device_info = {
            "id": device.id,
            "name": device.name,
            "model": device.model,
            "manufacturer": device.manufacturer,
            "sw_version": device.sw_version,
        }
        data["devices"].append(device_info)

    # Get entity diagnostics
    data["entities"] = []
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        entity_info = {
            "id": entity.entity_id,
            "name": entity.name,
            "original_name": entity.original_name,
            "domain": entity.domain,
            "disabled": entity.disabled,
            "device_id": entity.device_id,
            "unique_id": entity.unique_id,
        }
        data["entities"].append(entity_info)
        
    # Get client info and statistics if available
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        client = hass.data[DOMAIN][entry.entry_id].get("client")
        
        if client:
            # Add connection statistics
            data["statistics"]["connection"] = {
                "connected": client._connected,
                "connection_errors": client.connection_errors,
                "consecutive_errors": client.consecutive_errors,
                "last_successful_connection": client.last_successful_connection.isoformat() if client.last_successful_connection else None,
                "last_connect_attempt": client._last_connect_attempt.isoformat() if hasattr(client, "_last_connect_attempt") else None,
            }
            
            # Add modbus statistics
            data["statistics"]["modbus"] = {
                "host": async_redact_data({"host": client._host}, TO_REDACT)["host"],
                "port": client._port,
                "slave_id": client._client.unit_id if client._client else None,
            }
            
        if coordinator:
            # Add entity data from coordinator
            data["statistics"]["entities"] = {
                "last_update_success": coordinator.last_update_success,
                "last_update": coordinator.last_update.isoformat() if coordinator.last_update else None,
                "data": coordinator.data if coordinator.data else {},
            }
            
        # Check all entities for error counts
        data["statistics"]["entity_errors"] = {}
        for entity_entry in data["entities"]:
            entity_id = entity_entry["id"]
            entity = hass.states.get(entity_id)
            if entity and entity.domain in ["switch", "number", "sensor", "select"]:
                entity_obj = hass.data.get("entity_components", {}).get(entity.domain, {}).get(entity_id)
                if entity_obj and hasattr(entity_obj, "_error_count"):
                    data["statistics"]["entity_errors"][entity_id] = entity_obj._error_count
    
    return data 