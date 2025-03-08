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

# Advanced configuration options
CONF_ENABLE_PHASE_SENSORS = "enable_phase_sensors"
CONF_ENABLE_ERROR_SENSORS = "enable_error_sensors"
CONF_ENABLE_DAILY_ENERGY = "enable_daily_energy"
CONF_ENABLE_MONTHLY_ENERGY = "enable_monthly_energy"
CONF_ENABLE_YEARLY_ENERGY = "enable_yearly_energy"
CONF_READ_ONLY = "read_only"

# Default values for options
DEFAULT_ENABLE_PHASE_SENSORS = True
DEFAULT_ENABLE_ERROR_SENSORS = True
DEFAULT_ENABLE_DAILY_ENERGY = True
DEFAULT_ENABLE_MONTHLY_ENERGY = True
DEFAULT_ENABLE_YEARLY_ENERGY = True
DEFAULT_READ_ONLY = False

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

# New registers from Modbus registry spreadsheet
REG_ERROR = 2000               # Error codes in binary format
REG_CP_STATE = 2002            # Control Pilot state
REG_PREV_CP_STATE = 2003       # Previous Control Pilot state

# Individual phase measurements
REG_POWER_L1 = 4010            # Power of phase 1 in W
REG_POWER_L2 = 4011            # Power of phase 2 in W
REG_POWER_L3 = 4012            # Power of phase 3 in W

REG_CURRENT_L1 = 4014          # Current of phase 1 in mA
REG_CURRENT_L2 = 4015          # Current of phase 2 in mA  
REG_CURRENT_L3 = 4016          # Current of phase 3 in mA

REG_VOLTAGE_L1 = 4017          # RMS voltage of phase 1 in 0.1V
REG_VOLTAGE_L2 = 4018          # RMS voltage of phase 2 in 0.1V
REG_VOLTAGE_L3 = 4019          # RMS voltage of phase 3 in 0.1V

# Energy measurements
REG_ENERGY_L1 = 4000           # Energy phase 1 in mWh
REG_ENERGY_L2 = 4002           # Energy phase 2 in mWh
REG_ENERGY_L3 = 4004           # Energy phase 3 in mWh
REG_ENERGY_SUM = 4006          # Total energy in Wh

# CP State values

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

# CP State mapping from the spreadsheet
CP_STATES = {
    1: "Ready (+12V)",
    2: "EV Connected (+9V)",
    3: "Preparing (PWM +9V/-12V)",
    4: "EV Requires Charging (PWM +6V/-12V)",
    5: "Special Test State (+6V)",
    6: "Error: Ventilation Required",
    7: "Error: -12V Missing",
    8: "Error: CP Voltage Too Low",
    9: "Error: CP Voltage Too High",
    10: "Error: CP Shorted (0V)",
    11: "Unknown State",
    12: "Error: RCD Fault",
    13: "Error: Connector Missing"
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

# CP State icons mapping
CP_STATE_ICONS = {
    1: "mdi:ev-station",            # Ready
    2: "mdi:ev-plug-tesla",         # EV Connected
    3: "mdi:refresh-circle",        # Preparing
    4: "mdi:battery-charging-high", # EV Requires Charging
    5: "mdi:test-tube",             # Special Test State
    6: "mdi:fan",                   # Ventilation Required
    7: "mdi:flash-off",             # -12V Missing
    8: "mdi:arrow-down-bold",       # CP Voltage Too Low
    9: "mdi:arrow-up-bold",         # CP Voltage Too High
    10: "mdi:flash-alert",          # CP Shorted
    11: "mdi:help-circle",          # Unknown State
    12: "mdi:current-dc",           # RCD Fault
    13: "mdi:connection",           # Connector Missing
}

@property
def icon(self):
    """Return the icon to use based on state."""
    if self._is_on:
        return "mdi:ev-station"
    return "mdi:ev-station-off" 