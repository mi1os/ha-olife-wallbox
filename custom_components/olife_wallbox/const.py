"""Constants for the Olife Energy Wallbox integration."""

DOMAIN = "olife_wallbox"
PLATFORMS = ["switch", "number", "sensor"]

# Default values
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30

# Configuration
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Modbus registers (you'll need to replace these with actual values from Olife Energy documentation)
REG_CHARGING_ENABLE = 1000  # Example register for enabling/disabling charging
REG_CURRENT_LIMIT = 1001    # Example register for setting current limit
REG_CHARGING_CURRENT = 1002 # Example register for reading current charging current
REG_ENERGY_TOTAL = 1003     # Example register for total energy delivered
REG_CHARGING_STATUS = 1004  # Example register for charging status 