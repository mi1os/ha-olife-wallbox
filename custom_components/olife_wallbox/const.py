"""Constants for the Olife Energy Wallbox integration."""

DOMAIN = "olife_wallbox"
PLATFORMS = ["switch", "number", "sensor", "select"]

# Default values
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30
FAST_SCAN_INTERVAL = 5

# Configuration
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Modbus registers
# Read-Write registers
REG_CURRENT_LIMIT = 2106       # Current limit setting
REG_MAX_STATION_CURRENT = 5006 # Maximum station current
REG_LED_PWM = 5008             # LED PWM value
REG_CHARGING_ENABLE = 2105     # Register for enabling/disabling charging
REG_VERIFY_USER = 2101         # Register for user verification
REG_AUTOMATIC = 5003           # Register for automatic mode
REG_CHARGING_MODE = 2102       # Register for charging mode selection

# Read-Only registers
REG_WALLBOX_EV_STATE = 2104    # Wallbox EV state
REG_CHARGE_CURRENT = 2107      # Actual charging current
REG_CHARGE_ENERGY = 4106       # Energy delivered in current session
REG_CHARGE_POWER = 4113        # Current charging power

# Charging modes
CHARGING_MODES = ["fast", "solar", "spot", "off"]
CHARGING_MODE_VALUES = {
    "fast": 0,
    "solar": 1,
    "spot": 2,
    "off": 3
}

# EV State mapping
WALLBOX_EV_STATES = {
    1: "Cable Unplugged",
    2: "Cable Plugged",
    3: "User Authenticated",
    4: "Charging",
    5: "Car Suspended",
    6: "Current Below 6A",
    7: "No Authentication",
    90: "Error"
}

# EV State icons mapping
WALLBOX_EV_STATE_ICONS = {
    1: "mdi:ev-plug-disconnect",    # Cable unplugged
    2: "mdi:ev-plug",               # Cable plugged
    3: "mdi:account-check",         # User authenticated
    4: "mdi:battery-charging",      # Charging
    5: "mdi:car-electric",          # Car suspended
    6: "mdi:current-ac",            # Current below 6A
    7: "mdi:account-alert",         # No authentication
    90: "mdi:alert-circle"          # Error
}

@property
def icon(self):
    """Return the icon to use based on state."""
    if self._is_on:
        return "mdi:ev-station"
    return "mdi:ev-station-off" 