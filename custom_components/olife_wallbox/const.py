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

# Default values for advanced options
DEFAULT_ENABLE_PHASE_SENSORS = True
DEFAULT_ENABLE_ERROR_SENSORS = True
DEFAULT_ENABLE_DAILY_ENERGY = True
DEFAULT_ENABLE_MONTHLY_ENERGY = True
DEFAULT_ENABLE_YEARLY_ENERGY = True
DEFAULT_READ_ONLY = False

# Global station registers (not connector-specific)
REG_LED_PWM = 5008             # LED PWM value (global station setting)

# Connector 1 Registers (2000-2026, 4000-4019)
# EVSE-A registers
REG_ERROR = 2000               # Error in binary code
REG_VERIFY_USER = 2001         # Verify user by (cloud,rfid). If register is in 1 -> charging is enable
REG_CP_STATE = 2002            # Actual state on cp conductor
REG_PREV_CP_STATE = 2003       # Last CP state
REG_WALLBOX_EV_STATE = 2004    # Actual EV state
REG_PREV_EV_STATE = 2005       # Previous EV state
REG_CLOUD_CURRENT_LIMIT = 2006 # Current limit set by external devices (Cloud, Mobile app, etc.)
REG_CURRENT_LIMIT = 2007       # Actual set current - PP limit, ext. current regulator, cloudu, dipSwitches
REG_PP_CURRENT_LIMIT = 2008    # Current limit by PP resistor
REG_CONTACTOR_STATE = 2009     # Main contactor state
REG_CP_PWM_STATE = 2010        # Actual PWM value
REG_CP_HIGH = 2011             # Voltage of possitive PWM pulse
REG_CP_LOW = 2012              # Voltage of negative PWM pulse
REG_LOCK_STATE = 2013          # Lock state: 1=locked, 2=unlocked, 3=unlocking, 4=locking 0=uknown
REG_LOCK_SENSOR = 2014         # End sensor  1=locked, 2=unlocked, 0=uknown
REG_PP_RESISTOR = 2015         # PP resistor value
REG_LED_STATE = 2016           # Led state
REG_ADC_CP = 2017              # Value of CP in AD converter
REG_ADC_PP = 2018              # Value of PP in AD converter
REG_LOCK_RELEASE = 2019        # Emergency release of lock
REG_EXTERNAL_CURRENT_CONTROL = 2020 # External current control

# Wattmeter registers
# Individual phase measurements
REG_POWER_L1 = 4010            # Power of phase 1 in W truePOWER/RealPOWER
REG_POWER_L2 = 4011            # Power of phase 2 in W truePOWER/RealPOWER
REG_POWER_L3 = 4012            # Power of phase 3 in W truePOWER/RealPOWER
REG_POWER_SUM = 4013           # Power of all phases (1+2+3) in W truePOWER/RealPOWER

REG_CURRENT_L1 = 4014          # Current of phase 1 in mA
REG_CURRENT_L2 = 4015          # Current of phase 2 in mA  
REG_CURRENT_L3 = 4016          # Current of phase 3 in mA

REG_VOLTAGE_L1 = 4017          # RMS voltage of phase 1 in 0.1V
REG_VOLTAGE_L2 = 4018          # RMS voltage of phase 2 in 0.1V
REG_VOLTAGE_L3 = 4019          # RMS voltage of phase 3 in 0.1V

# Energy measurements
REG_ENERGY_L1 = 4000           # Energy phase 1 in mWh (x0,001 Wh)
REG_ENERGY_L2 = 4002           # Energy phase 2 in mWh (x0,001 Wh)
REG_ENERGY_L3 = 4004           # Energy phase 3 in mWh (x0,001 Wh)
REG_ENERGY_SUM = 4006          # Total station energy in mWh (x1 Wh)
REG_ENERGY_FLASH = 4008        # Energy in Wh, saved to flash every 24 hours

# Connector 2 Registers (if present, 2100-2126, 4100-4119)
# EVSE-A registers (second connector)
REG_ERROR_2 = 2100             # Error in binary code (connector 2)
REG_VERIFY_USER_2 = 2101       # Verify user (connector 2)
REG_CP_STATE_2 = 2102          # Actual state on cp conductor (connector 2)
REG_PREV_CP_STATE_2 = 2103     # Last CP state (connector 2)
REG_WALLBOX_EV_STATE_2 = 2104  # Actual EV state (connector 2)
REG_PREV_EV_STATE_2 = 2105     # Previous EV state (connector 2)
REG_CLOUD_CURRENT_LIMIT_2 = 2106 # Current limit set by external devices (connector 2)
REG_CURRENT_LIMIT_2 = 2107     # Actual set current (connector 2)
REG_PP_CURRENT_LIMIT_2 = 2108  # Current limit by PP resistor (connector 2)
REG_CONTACTOR_STATE_2 = 2109   # Main contactor state (connector 2)
REG_CP_PWM_STATE_2 = 2110      # Actual PWM value (connector 2)
REG_CP_HIGH_2 = 2111           # Voltage of possitive PWM pulse (connector 2)
REG_CP_LOW_2 = 2112            # Voltage of negative PWM pulse (connector 2)
REG_LOCK_STATE_2 = 2113        # Lock state (connector 2)
REG_LOCK_SENSOR_2 = 2114       # End sensor (connector 2)
REG_PP_RESISTOR_2 = 2115       # PP resistor value (connector 2)
REG_LED_STATE_2 = 2116         # Led state (connector 2)
REG_ADC_CP_2 = 2117            # Value of CP in AD converter (connector 2)
REG_ADC_PP_2 = 2118            # Value of PP in AD converter (connector 2)
REG_LOCK_RELEASE_2 = 2119      # Emergency release of lock (connector 2)
REG_EXTERNAL_CURRENT_CONTROL_2 = 2120 # External current control (connector 2)

# Wattmeter registers (second connector)
REG_POWER_L1_2 = 4110          # Power of phase 1 in W truePOWER/RealPOWER (connector 2)
REG_POWER_L2_2 = 4111          # Power of phase 2 in W truePOWER/RealPOWER (connector 2)
REG_POWER_L3_2 = 4112          # Power of phase 3 in W truePOWER/RealPOWER (connector 2)
REG_POWER_SUM_2 = 4113         # Power of all phases (1+2+3) in W truePOWER/RealPOWER (connector 2)

REG_CURRENT_L1_2 = 4114        # Current of phase 1 in mA (connector 2)
REG_CURRENT_L2_2 = 4115        # Current of phase 2 in mA (connector 2)
REG_CURRENT_L3_2 = 4116        # Current of phase 3 in mA (connector 2)

REG_VOLTAGE_L1_2 = 4117        # RMS voltage of phase 1 in 0.1V (connector 2)
REG_VOLTAGE_L2_2 = 4118        # RMS voltage of phase 2 in 0.1V (connector 2)
REG_VOLTAGE_L3_2 = 4119        # RMS voltage of phase 3 in 0.1V (connector 2)

REG_ENERGY_L1_2 = 4100         # Energy phase 1 in mWh (x0,001 Wh) (connector 2)
REG_ENERGY_L2_2 = 4102         # Energy phase 2 in mWh (x0,001 Wh) (connector 2)
REG_ENERGY_L3_2 = 4104         # Energy phase 3 in mWh (x0,001 Wh) (connector 2)
REG_ENERGY_SUM_2 = 4106        # Total station energy in mWh (x1 Wh) (connector 2)
REG_ENERGY_FLASH_2 = 4108      # Energy in Wh, saved to flash every 24 hours (connector 2)

# Missing registers in our original implementation that we need to map
REG_CHARGE_CURRENT = 2007      # Using current limit register as charge current
REG_CHARGE_ENERGY = 4006       # Using total energy as charge energy
REG_CHARGE_POWER = 4010        # Using phase 1 power as charge power for simplicity
REG_MAX_STATION_CURRENT = 2008 # Using PP current limit as max station current
REG_CHARGING_ENABLE = 2001     # Using verify user as charging enable
REG_AUTOMATIC = 2001           # Not directly available, using verify user

# Second connector equivalent mappings
REG_CHARGE_CURRENT_2 = 2107    # Using current limit register as charge current (connector 2)
REG_CHARGE_ENERGY_2 = 4106     # Using total energy as charge energy (connector 2)
REG_CHARGE_POWER_2 = 4110      # Using phase 1 power as charge power for simplicity (connector 2)
REG_MAX_STATION_CURRENT_2 = 2108 # Using PP current limit as max station current (connector 2)
REG_CHARGING_ENABLE_2 = 2101   # Using verify user as charging enable (connector 2)
REG_AUTOMATIC_2 = 2101         # Not directly available, using verify user (connector 2)

# Device information registers
REG_DEVICE_INFO_START = 6000   # Device information start
REG_FLASH_STATE = 6000         # 0 - data v RAM; 1 = data ve FLASH
REG_HW_VERSION = 6001          # Hardware version (hw revision)
REG_SW_VERSION = 6002          # Software version (sw revision)
REG_SN_FIRST_PART = 6003       # First 3 numbers of serial number (e.g. "014")
REG_SN_FIRST_RESERVE = 6004    # Serial number reserve
REG_SN_LAST_PART = 6005        # Last 3 numbers of serial number (e.g. "014")
REG_SN_LAST_RESERVE = 6006     # Serial number reserve
REG_PN_TYPE = 6007             # Type of station, two numbers. First numb.: WB = 1, DB = 2, ST = 3, second number: Base = 1 Smart = 2 (e.g. "32" = ST SMART)
REG_PN_LEFT = 6008             # Left - type of output connector, first number is Type - (mennekes = 2, yazaki = 1); second number (1= Socket, 2 = Coil cable, 3 straight cable)
REG_PN_RIGHT = 6009            # Right - type of output connector, first number is Type - (mennekes = 2, yazaki = 1); second number (1= Socket, 2 = Coil cable, 3 straight cable)
REG_PN_RESERVE = 6010          # Reserve
REG_YEAR_MONTH = 6011          # 'YYMM (YY year, MM month, )' e.g. "2107"
REG_DAY_HOUR = 6012            # DDHH (DD Day, HH hour) e.g. "3015"
REG_NUM_CONNECTORS = 6015      # Connector count (active connectors)

# CP State values

# EV State mapping
WALLBOX_EV_STATES = {
    1: "EV Unplugged",
    2: "EV Connected",
    3: "EV Verified",
    4: "Charging",
    5: "Charging Interrupted",
    6: "Current Below 6A",
    7: "Cloud Stopped",
    8: "Tester Charging",
    90: "Error"
}

# Detailed EV state descriptions for attributes
WALLBOX_EV_STATE_DESCRIPTIONS = {
    1: "EV unplugged",
    2: "EV connected (CP state from 12V to 9V)",
    3: "EV verified (CP state from 9V to 9V with PWM)",
    4: "EV charging, main contactor is ON (CP state in 6V PWM)",
    5: "EV charging interrupted (100% SoC or key) (CP state from 6V PWM to 9V PWM)",
    6: "Charging stopped by current regulator (Current under 6A) (CP state from 6V PWM to 9V)",
    7: "Charging stopped by cloud (CP state from 6V PWM to 9V)",
    8: "Charging by tester",
    90: "EV error"
}

# CP State mapping
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
    12: "Error: RCD Fault"
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