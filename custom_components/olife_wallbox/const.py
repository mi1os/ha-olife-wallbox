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
REG_MAX_STATION_CURRENT = 5006  # Global maximum station current (for the entire wallbox)
REG_AUTOMATIC = 5003           # If set to 1, charging starts automatically after car connection
REG_AUTOMATIC_DIPSWITCH_ON = 5004  # If set to 1, automatic mode is driven by dipSwitch state
REG_MAX_CURRENT_DIPSWITCH_ON = 5005  # If set to 1, max current controlled by DIPSWITCH, 0 - controlled by 5006
REG_BALANCING_EXTERNAL_CURRENT = 5007  # If set to 1, controlled by external LOCAL wattmeter
REG_RS485_ID = 5023            # Slave modbus ID (0-16)
REG_WATTMETER_MODE = 5024      # 0 = Olife internal(default), 1 = ORNO WE516

# Connector A Registers (2000-2026, 4000-4019)
# EVSE-A registers
REG_ERROR_A = 2000              # Error in binary code
REG_VERIFY_USER_A = 2001        # Verify user by (cloud,rfid). If register is in 1 -> charging is enable
REG_CP_STATE_A = 2002           # Actual state on cp conductor
REG_PREV_CP_STATE_A = 2003      # Last CP state
REG_WALLBOX_EV_STATE_A = 2004   # Actual EV state
REG_PREV_EV_STATE_A = 2005      # Previous EV state
REG_CLOUD_CURRENT_LIMIT_A = 2006 # Current limit set by external devices (Cloud, Mobile app, etc.)
REG_CURRENT_LIMIT_A = 2007      # Actual set current - PP limit, ext. current regulator, cloudu, dipSwitches
REG_PP_CURRENT_LIMIT_A = 2008   # Current limit by PP resistor
REG_CONTACTOR_STATE_A = 2009    # Main contactor state
REG_CP_PWM_STATE_A = 2010       # Actual PWM value
REG_CP_HIGH_A = 2011            # Voltage of possitive PWM pulse
REG_CP_LOW_A = 2012             # Voltage of negative PWM pulse
REG_LOCK_STATE_A = 2013         # Lock state: 1=locked, 2=unlocked, 3=unlocking, 4=locking 0=uknown
REG_LOCK_SENSOR_A = 2014        # End sensor  1=locked, 2=unlocked, 0=uknown
REG_PP_RESISTOR_A = 2015        # PP resistor value
REG_LED_STATE_A = 2016          # Led state
REG_ADC_CP_A = 2017             # Value of CP in AD converter
REG_ADC_PP_A = 2018             # Value of PP in AD converter
REG_LOCK_RELEASE_A = 2019       # Emergency release of lock
REG_EXTERNAL_CURRENT_CONTROL_A = 2020 # External current control

# Wattmeter registers
# Individual phase measurements
REG_POWER_L1_A = 4010           # Power of phase 1 in W truePOWER/RealPOWER
REG_POWER_L2_A = 4011           # Power of phase 2 in W truePOWER/RealPOWER
REG_POWER_L3_A = 4012           # Power of phase 3 in W truePOWER/RealPOWER
REG_POWER_SUM_A = 4013          # Power of all phases (1+2+3) in W truePOWER/RealPOWER

REG_CURRENT_L1_A = 4014         # Current of phase 1 in mA
REG_CURRENT_L2_A = 4015         # Current of phase 2 in mA  
REG_CURRENT_L3_A = 4016         # Current of phase 3 in mA

REG_VOLTAGE_L1_A = 4017         # RMS voltage of phase 1 in 0.1V
REG_VOLTAGE_L2_A = 4018         # RMS voltage of phase 2 in 0.1V
REG_VOLTAGE_L3_A = 4019         # RMS voltage of phase 3 in 0.1V

# Energy measurements
REG_ENERGY_L1_A = 4000          # Energy phase 1 in mWh (x0,001 Wh)
REG_ENERGY_L2_A = 4002          # Energy phase 2 in mWh (x0,001 Wh)
REG_ENERGY_L3_A = 4004          # Energy phase 3 in mWh (x0,001 Wh)
REG_ENERGY_SUM_A = 4006         # Total station energy in mWh (x1 Wh)
REG_ENERGY_FLASH_A = 4008        # Energy in Wh, saved to flash every 24 hours

# Connector B Registers (if present, 2100-2126, 4100-4119)
# EVSE-A registers (second connector)
REG_ERROR_B = 2100              # Error in binary code (connector B)
REG_VERIFY_USER_B = 2101        # Verify user (connector B)
REG_CP_STATE_B = 2102           # Actual state on cp conductor (connector B)
REG_PREV_CP_STATE_B = 2103      # Last CP state (connector B)
REG_WALLBOX_EV_STATE_B = 2104   # Actual EV state (connector B)
REG_PREV_EV_STATE_B = 2105      # Previous EV state (connector B)
REG_CLOUD_CURRENT_LIMIT_B = 2106 # Current limit set by external devices (connector B)
REG_CURRENT_LIMIT_B = 2107      # Actual set current (connector B)
REG_PP_CURRENT_LIMIT_B = 2108   # Current limit by PP resistor (connector B)
REG_CONTACTOR_STATE_B = 2109    # Main contactor state (connector B)
REG_CP_PWM_STATE_B = 2110        # Actual PWM value (connector B)
REG_CP_HIGH_B = 2111            # Voltage of possitive PWM pulse (connector B)
REG_CP_LOW_B = 2112             # Voltage of negative PWM pulse (connector B)
REG_LOCK_STATE_B = 2113         # Lock state (connector B)
REG_LOCK_SENSOR_B = 2114        # End sensor (connector B)
REG_PP_RESISTOR_B = 2115         # PP resistor value (connector B)
REG_LED_STATE_B = 2116           # Led state (connector B)
REG_ADC_CP_B = 2117             # Value of CP in AD converter (connector B)
REG_ADC_PP_B = 2118             # Value of PP in AD converter (connector B)
REG_LOCK_RELEASE_B = 2119        # Emergency release of lock (connector B)
REG_EXTERNAL_CURRENT_CONTROL_B = 2120 # External current control (connector B)

# Wattmeter registers (second connector)
REG_POWER_L1_B = 4110           # Power of phase 1 in W truePOWER/RealPOWER (connector B)
REG_POWER_L2_B = 4111           # Power of phase 2 in W truePOWER/RealPOWER (connector B)
REG_POWER_L3_B = 4112           # Power of phase 3 in W truePOWER/RealPOWER (connector B)
REG_POWER_SUM_B = 4113          # Sum of power on L1+L2+L3 (connector B)

REG_CURRENT_L1_B = 4114         # Current of phase 1 in mA (connector B)
REG_CURRENT_L2_B = 4115         # Current of phase 2 in mA (connector B)
REG_CURRENT_L3_B = 4116         # Current of phase 3 in mA (connector B)

REG_VOLTAGE_L1_B = 4117         # RMS voltage of phase 1 in 0.1V (connector B)
REG_VOLTAGE_L2_B = 4118         # RMS voltage of phase 2 in 0.1V (connector B)
REG_VOLTAGE_L3_B = 4119         # RMS voltage of phase 3 in 0.1V (connector B)

REG_ENERGY_L1_B = 4100          # Energy phase 1 in mWh (x0,001 Wh) (connector B)
REG_ENERGY_L2_B = 4102          # Energy phase 2 in mWh (x0,001 Wh) (connector B)
REG_ENERGY_L3_B = 4104          # Energy phase 3 in mWh (x0,001 Wh) (connector B)
REG_ENERGY_SUM_B = 4106         # Total station energy in mWh (x1 Wh) (connector B)
REG_ENERGY_FLASH_B = 4108        # Energy in Wh, saved to flash every 24 hours (connector B)

# Missing registers in our original implementation that we need to map
REG_CHARGE_CURRENT_A = 2007     # Using current limit register as charge current (connector A)
REG_CHARGE_ENERGY_A = 4006      # Using total energy as charge energy (connector A)
REG_CHARGE_POWER_A = 4010        # Using phase 1 power as charge power for simplicity (connector A)
REG_MAX_STATION_CURRENT_A = 2008 # Using PP current limit as max station current (connector A)
REG_CHARGING_ENABLE_A = 2001      # Using verify user as charging enable (connector A)
REG_AUTOMATIC_A = 2001           # Not directly available, using verify user (connector A)

# Second connector equivalent mappings
REG_CHARGE_CURRENT_B = 2107     # Using current limit register as charge current (connector B)
REG_CHARGE_ENERGY_B = 4106        # Using total energy as charge energy (connector B)
REG_CHARGE_POWER_B = 4110          # Using phase 1 power as charge power for simplicity (connector B)
REG_MAX_STATION_CURRENT_B = 2108   # Using PP current limit as max station current (connector B)
REG_CHARGING_ENABLE_B = 2101        # Using verify user as charging enable (connector B)
REG_AUTOMATIC_B = 2101             # Not directly available, using verify user (connector B)

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

# Wattmeter detection
REG_EXTERNAL_WATTMETER = 6013  # 0 - disconnected, 1 - connected

# External Wattmeter registers (4200-4219)
REG_EXT_ENERGY_L1 = 4200       # Energy phase 1 in mWh (x0,001 Wh) (external wattmeter)
REG_EXT_ENERGY_L2 = 4202       # Energy phase 2 in mWh (x0,001 Wh) (external wattmeter)
REG_EXT_ENERGY_L3 = 4204       # Energy phase 3 in mWh (x0,001 Wh) (external wattmeter)
REG_EXT_ENERGY_SUM = 4206      # Total station energy in mWh (x1 Wh) (external wattmeter)
REG_EXT_ENERGY_FLASH = 4208    # Energy in Wh, saved to flash every 24 hours (external wattmeter)
REG_EXT_POWER_L1 = 4210        # Power of phase 1 in W truePOWER/RealPOWER (external wattmeter)
REG_EXT_POWER_L2 = 4211        # Power of phase 2 in W truePOWER/RealPOWER (external wattmeter)
REG_EXT_POWER_L3 = 4212        # Power of phase 3 in W truePOWER/RealPOWER (external wattmeter)
REG_EXT_POWER_SUM = 4213       # Power of all phases (1+2+3) in W truePOWER/RealPOWER (external wattmeter)
REG_EXT_CURRENT_L1 = 4214      # Current of phase 1 in mA (external wattmeter)
REG_EXT_CURRENT_L2 = 4215      # Current of phase 2 in mA (external wattmeter)
REG_EXT_CURRENT_L3 = 4216      # Current of phase 3 in mA (external wattmeter)
REG_EXT_VOLTAGE_L1 = 4217      # RMS voltage of phase 1 in 0.1V (external wattmeter)
REG_EXT_VOLTAGE_L2 = 4218      # RMS voltage of phase 2 in 0.1V (external wattmeter)
REG_EXT_VOLTAGE_L3 = 4219      # RMS voltage of phase 3 in 0.1V (external wattmeter)

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
    9: "RCD DC Sensor Fault",
    10: "EVSE Error",
    13: "No Second Connector",
    90: "Error"
}

# Detailed EV state descriptions for attributes
WALLBOX_EV_STATE_DESCRIPTIONS = {
    1: "EV unplugged",
    2: "EV connected (Change CP state from unplug 12V to connected 9V)",
    3: "EV verified (Change CP state from 9V to 9V with PWM)",
    4: "EV charging, main contactor is ON (CP state in 6V PWM)",
    5: "EV interrupted charging (100% SoC, interrupt by key) (change CP state from 6V PWM to 9V PWM)",
    6: "Charging stopped by external current regulator/cloud (Current is set under 6A) (change CP state from 6V PWM to 9V)",
    7: "Charging stopped by external regulator/cloud (change CP state from 6V PWM to 9V)",
    8: "Charging by tester",
    9: "Error RCD DC sensor fault. 6mA DC leakage detected, need to check and restart for clear error",
    10: "Error EVSE error see CP state",
    13: "EVSE has not second connector it is probab",
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
    12: "Error: RCD Fault",
    13: "Error: Connector Missing"
}

# CP State detailed descriptions
CP_STATE_DESCRIPTIONS = {
    1: "STATE_H12 - EVSE ready +12V",
    2: "STATE_H9 - EV connected +9V",
    3: "STATE_PWM9 - Preparing (EV connected, user verified, PWM +9V -12V, waiting for car)",
    4: "STATE_PWM6 - EV require charging, PWM +6V -12V",
    5: "STATE_H6 - Tester special state",
    6: "STATE_E_3 - Error EV require ventilation",
    7: "STATE_E_L12 - Error -12V",
    8: "STATE_E_MIN - Error out of min limit",
    9: "STATE_E_MAX - Error out of max limit",
    10: "STATE_E_0 - Error CP=0V -> CP short circuit",
    11: "STATE_UNKNOWN - Unknown",
    12: "STATE_E_RCD_FAULT - Residual current fault",
    13: "STATE_CONNECTOR_MISS - EVSE has not second connector"
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
    8: "mdi:test-tube",             # Tester charging
    9: "mdi:current-dc",            # RCD DC sensor fault
    10: "mdi:alert-circle",         # EVSE Error
    13: "mdi:connection",           # No second connector
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