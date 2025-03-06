"""Constants for the Olife Energy Wallbox integration."""

DOMAIN = "olife_wallbox"
PLATFORMS = ["switch", "number", "sensor"]

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

# Read-Only registers
REG_WALLBOX_EV_STATE = 2104    # Wallbox EV state
REG_CHARGE_CURRENT = 2107      # Actual charging current
REG_CHARGE_ENERGY = 4106       # Energy delivered in current session
REG_CHARGE_POWER = 4113        # Current charging power 