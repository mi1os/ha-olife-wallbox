"""Device triggers for Olife Energy Wallbox."""
import logging
from typing import Any, Dict, List, Optional, Callable

import voluptuous as vol

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import state as state_trigger

from .const import DOMAIN, WALLBOX_EV_STATES

_LOGGER = logging.getLogger(__name__)

# Trigger types
TRIGGER_TYPE_EV_CONNECTED = "ev_connected"
TRIGGER_TYPE_EV_DISCONNECTED = "ev_disconnected"
TRIGGER_TYPE_CHARGING_STARTED = "charging_started"
TRIGGER_TYPE_CHARGING_STOPPED = "charging_stopped"
TRIGGER_TYPE_AUTHENTICATED = "authenticated"
TRIGGER_TYPE_ERROR = "error"

# State value mapping for triggers
TRIGGER_STATE_MAP = {
    TRIGGER_TYPE_EV_CONNECTED: 2,       # Cable Plugged
    TRIGGER_TYPE_EV_DISCONNECTED: 1,    # Cable Unplugged
    TRIGGER_TYPE_CHARGING_STARTED: 4,   # Charging
    TRIGGER_TYPE_CHARGING_STOPPED: None,  # Any non-charging state
    TRIGGER_TYPE_AUTHENTICATED: 3,      # User Authenticated
    TRIGGER_TYPE_ERROR: 90,             # Error
}

TRIGGER_TYPES = {
    TRIGGER_TYPE_EV_CONNECTED,
    TRIGGER_TYPE_EV_DISCONNECTED,
    TRIGGER_TYPE_CHARGING_STARTED,
    TRIGGER_TYPE_CHARGING_STOPPED,
    TRIGGER_TYPE_AUTHENTICATED,
    TRIGGER_TYPE_ERROR,
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> List[Dict[str, Any]]:
    """List device triggers for Olife Energy Wallbox devices."""
    registry = er.async_get(hass)
    triggers = []

    # Find the EV state sensor entity for this device
    for entry in er.async_entries_for_device(registry, device_id):
        if entry.domain != "sensor":
            continue

        if entry.original_name == "EV State" and entry.unique_id and DOMAIN in entry.unique_id:
            # This is our EV state sensor, add triggers for it
            for trigger_type in TRIGGER_TYPES:
                trigger_name = trigger_type.replace("_", " ").title()
                triggers.append(
                    {
                        CONF_PLATFORM: "device",
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_TYPE: trigger_type,
                        "name": f"When {trigger_name}",
                    }
                )
            break

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Callable,
    automation_info: Dict[str, Any],
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_type = config[CONF_TYPE]
    device_id = config[CONF_DEVICE_ID]
    registry = er.async_get(hass)

    # Find the EV state sensor entity for this device
    ev_state_entity_id = None
    for entry in er.async_entries_for_device(registry, device_id):
        if (
            entry.domain == "sensor"
            and entry.original_name == "EV State"
            and entry.unique_id
            and DOMAIN in entry.unique_id
        ):
            ev_state_entity_id = entry.entity_id
            break

    if not ev_state_entity_id:
        raise InvalidDeviceAutomationConfig(
            f"Could not find EV state entity for device {device_id}"
        )

    # Set up our state trigger configuration
    trigger_config = {
        CONF_PLATFORM: "state",
        CONF_ENTITY_ID: ev_state_entity_id,
    }

    # Special case for "charging_stopped" since we need to monitor transitions from
    # charging (4) to any other state
    if trigger_type == TRIGGER_TYPE_CHARGING_STOPPED:
        trigger_config["from"] = WALLBOX_EV_STATES.get(4)  # From "Charging"
    else:
        # For other triggers, we set the "to" state
        state_value = TRIGGER_STATE_MAP.get(trigger_type)
        if state_value is not None:
            readable_state = WALLBOX_EV_STATES.get(state_value, STATE_UNKNOWN)
            trigger_config["to"] = readable_state

    return await state_trigger.async_attach_trigger(
        hass, trigger_config, action, automation_info, platform_type="device"
    ) 