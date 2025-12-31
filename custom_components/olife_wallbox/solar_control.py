"""Solar optimization logic for Olife Energy Wallbox."""
import logging
import asyncio
from typing import Optional

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from .const import (
    REG_CLOUD_CURRENT_LIMIT_B,
    REG_MAX_STATION_CURRENT,
)

_LOGGER = logging.getLogger(__name__)

class OlifeSolarOptimizer:
    """Class to handle solar optimization logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        client,
        solar_entity_id: str,
        charging_phases: int,
        min_current_offset: int,
        max_station_current_entity_id: str = None
    ):
        """Initialize the solar optimizer."""
        self.hass = hass
        self._client = client
        self._solar_entity_id = solar_entity_id
        self._charging_phases = charging_phases
        self._min_current_offset = min_current_offset
        self._max_station_current_entity_id = max_station_current_entity_id
        self._remove_listener = None
        self._current_limit = 6  # Default start
        
    def set_offset(self, offset: int):
        """Update the offset value at runtime."""
        self._min_current_offset = offset
        _LOGGER.debug("Solar optimizer offset updated to %sA", offset)
        
    async def async_enable(self):
        """Enable the solar optimizer."""
        if self._remove_listener:
            return

        _LOGGER.info("Enabling solar optimizer for entity %s", self._solar_entity_id)
        
        # Track state changes of the solar entity
        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self._solar_entity_id],
            self._async_on_state_change
        )
        
        # Trigger an initial update
        current_state = self.hass.states.get(self._solar_entity_id)
        if current_state:
            await self._process_solar_update(current_state)

    def disable(self):
        """Disable the solar optimizer."""
        if self._remove_listener:
            _LOGGER.info("Disabling solar optimizer")
            self._remove_listener()
            self._remove_listener = None

    @callback
    async def _async_on_state_change(self, event):
        """Handle state change events."""
        new_state = event.data.get("new_state")
        if new_state:
            await self._process_solar_update(new_state)

    async def _process_solar_update(self, state: State):
        """Process a state update from the solar entity."""
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            # Parse solar power value (Watts)
            # Positive = Export/Excess, Negative = Import
            # Validate state before conversion
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.debug("Solar power sensor is %s, skipping calculation", state.state)
                return

            # Attempt conversion with validation
            try:
                solar_power = float(state.state)
            except (ValueError, TypeError) as e:
                _LOGGER.error("Invalid solar power value '%s': %s", state.state, e)
                return

            # Additional validation for reasonable values
            if abs(solar_power) > 100000:  # Sanity check for > 100kW
                _LOGGER.warning("Unusually high solar power value: %s W", solar_power)
                return

            # Calculate available current per phase
            # Power = Voltage * Current * Phases
            # Current = Power / (Voltage * Phases)
            voltage = 230  # Assuming 230V

            # Validate charging phases to prevent division by zero
            if self._charging_phases <= 0:
                _LOGGER.error("Invalid charging phases configuration: %s", self._charging_phases)
                return

            # Calculate current from excess power
            calculated_current = solar_power / (voltage * self._charging_phases)
            
            # Only add offset if calculated current is below 6A
            if calculated_current < 6:
                target_current = calculated_current + self._min_current_offset
            else:
                target_current = calculated_current
            
            # Round to nearest integer
            target_current_int = int(round(target_current))
            
            # Get max station current if available, otherwise default to 32A
            max_current = 32
            if self._max_station_current_entity_id:
                max_state = self.hass.states.get(self._max_station_current_entity_id)
                if max_state and max_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    try:
                        max_current = int(float(max_state.state))
                    except ValueError:
                        pass
            
            # Clamp the value
            # If calculated value is < 6A, we still send it. 
            # The wallbox should handle < 6A by stopping charging or staying at min.
            # However, standard EV charging minimum is 6A.
            # If we send < 6A, we are effectively asking to stop or pause.
            
            final_current = target_current_int
            
            # Clamp to min 0
            if final_current < 0:
                final_current = 0
            
            # Clamp to max
            if final_current > max_current:
                final_current = max_current
                
            # Check if we need to update
            # We only update if the value has changed to avoid spamming Modbus
            # But we also need to be careful about not updating too frequently if solar fluctuates wildly.
            # For now, we implement basic change detection.
            
            if final_current != self._current_limit:
                _LOGGER.debug(
                    "Solar update: Power=%s W, Calc=%s A, Offset=%s A, Target=%s A, Final=%s A",
                    solar_power, calculated_current, self._min_current_offset, target_current, final_current
                )
                
                # Write to Modbus
                # Using REG_CLOUD_CURRENT_LIMIT_B as per number.py implementation
                # We might need to respect the connector selection logic from number.py if we want to be 100% correct for all models
                # But for now assuming Connector B is the primary controllable one as per existing code
                
                # Note: We are not checking if the write was successful here to keep it simple async
                # In a robust implementation we might want to retry or handle errors
                await self._client.write_register(REG_CLOUD_CURRENT_LIMIT_B, final_current)
                self._current_limit = final_current
                
        except ValueError:
            _LOGGER.warning("Invalid solar power value: %s", state.state)
        except Exception as ex:
            _LOGGER.error("Error processing solar update: %s", ex)
