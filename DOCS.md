# Olife Energy Wallbox Integration Documentation

## Overview

The Olife Energy Wallbox integration for Home Assistant provides comprehensive monitoring and control of Olife Energy electric vehicle charging stations via Modbus TCP protocol. This integration supports both single and dual-connector wallboxes with advanced features like solar optimization and energy tracking.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Features](#features)
4. [Entities](#entities)
5. [Services](#services)
6. [Automation Examples](#automation-examples)
7. [Troubleshooting](#troubleshooting)
8. [Development](#development)

## Installation

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant
2. Go to HACS > Integrations
3. Click the "+" button and select "Custom repositories"
4. Add the repository URL: `https://github.com/mi1os/ha-olife-wallbox`
5. Select "Integration" as category
6. Search for "Olife Energy Wallbox" and install

### Manual Installation

1. Download the latest release from the repository
2. Extract the archive
3. Copy the `olife_wallbox` folder to your `custom_components` directory
4. Restart Home Assistant

## Configuration

### Basic Setup

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Olife Energy Wallbox"
4. Enter the following details:
   - **Host**: IP address of your Wallbox (e.g., 192.168.1.100)
   - **Port**: Modbus TCP port (default: 502)
   - **Slave ID**: Modbus slave ID (default: 1)
   - **Name**: Display name for your device

### Advanced Configuration

Access advanced options by going to Settings > Devices & Services > Olife Energy Wallbox > Configure:

- **Read-Only Mode**: Enable to prevent any control operations
- **Scan Interval**: Update frequency (5-300 seconds)
- **Enable Phase Sensors**: Detailed per-phase measurements
- **Enable Error Sensors**: Error code and CP state sensors
- **Energy Tracking**: Daily, monthly, yearly energy counters
- **Solar Power Entity**: Entity ID for solar power sensor (W)
- **Charging Phases**: Number of phases (1 or 3)
- **Min Current Offset**: Offset for solar calculations

## Features

### Multi-Connector Support

The integration automatically detects single or dual-connector wallboxes:
- Single connector: Uses Connector B registers
- Dual connector: Creates entities for both Connector A and B

### Real-time Monitoring

- EV connection state
- Charging status
- Error conditions
- Power consumption
- Energy tracking

### Solar Optimization

Automatically adjusts charging current based on excess solar power:
- Monitors solar power export
- Calculates available current
- Updates charging limit dynamically
- Respects minimum 6A threshold

### Energy Dashboard Integration

Full support for Home Assistant Energy Dashboard with:
- Total energy consumption
- Per-phase energy tracking
- Daily/monthly/yearly statistics
- Automatic state class configuration

## Entities

### Sensors

#### Status Sensors
- `sensor.{name}_ev_state` - Current EV state (Unplugged, Connected, Charging, etc.)
- `sensor.{name}_cp_state` - Control Pilot state
- `sensor.{name}_error_code` - Error code with binary flag decoding

#### Power and Energy
- `sensor.{name}_charge_power` - Current charging power (W)
- `sensor.{name}_charge_current` - Charging current (A)
- `sensor.{name}_energy_total` - Total energy consumed (kWh)
- `sensor.{name}_daily_charge_energy` - Today's energy (Wh)
- `sensor.{name}_monthly_charge_energy` - This month's energy (Wh)
- `sensor.{name}_yearly_charge_energy` - This year's energy (kWh)

#### Per-Phase Measurements (if enabled)
- `sensor.{name}_power_l1/l2/l3` - Power per phase (W)
- `sensor.{name}_current_l1/l2/l3` - Current per phase (A)
- `sensor.{name}_voltage_l1/l2/l3` - Voltage per phase (V)
- `sensor.{name}_energy_l1/l2/l3` - Energy per phase (kWh)

#### Device Information
- `sensor.{name}_hw_version` - Hardware version
- `sensor.{name}_sw_version` - Software version
- `sensor.{name}_serial_number` - Device serial number

### Controls

#### Switches
- `switch.{name}_charging` - Enable/disable charging
- `switch.{name}_automatic_mode` - Toggle automatic mode
- `switch.{name}_verify_user` - User verification control

#### Numbers
- `number.{name}_current_limit` - Set charging current limit (0-32A)
- `number.{name}_max_station_current` - Maximum station current (0-63A)
- `number.{name}_led_brightness` - LED brightness (0-1000)

#### Buttons
- `button.{name}_charging_authorization` - Authorize charging

## Services

### Core Services

#### Start/Stop Charging
```yaml
service: olife_wallbox.start_charge
target:
  device_id: your_device_id
```

#### Set Current Limit
```yaml
service: olife_wallbox.set_current_limit
target:
  device_id: your_device_id
data:
  current_limit: 16
```

#### Reset Energy Counters
```yaml
service: olife_wallbox.reset_energy_counters
target:
  device_id: your_device_id
data:
  daily: true
  monthly: true
  yearly: true
```

#### Reload Integration
```yaml
service: olife_wallbox.reload
target:
  device_id: your_device_id
```

## Automation Examples

### Auto-start Charging at Low Tariff
```yaml
automation:
  - alias: "Start charging at night tariff"
    trigger:
      platform: time
      at: "23:00:00"
    condition:
      - condition: state
        entity_id: sensor.wallbox_ev_state
        state: "EV Connected"
    action:
      - service: olife_wallbox.start_charge
        target:
          device_id: your_wallbox_device_id
```

### Solar-optimized Charging
```yaml
automation:
  - alias: "Adjust charging based on solar"
    trigger:
      platform: state
      entity_id: sensor.solar_power_excess
    action:
      - service: olife_wallbox.set_current_limit
        target:
          device_id: your_wallbox_device_id
data:
  current_limit: "{{ [(states('sensor.solar_power_excess')|float / 230 / 3), 6]|max }}"
```

### Charging Completion Notification
```yaml
automation:
  - alias: "Notify when charging complete"
    trigger:
      platform: state
      entity_id: sensor.wallbox_ev_state
      from: "Charging"
      to: "EV Connected"
    action:
      - service: notify.mobile_app
        data:
          message: "Charging completed!"
          title: "Wallbox Status"
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Wallbox

**Solutions**:
1. Verify IP address is correct
2. Check Modbus TCP is enabled on Wallbox
3. Ensure network connectivity
4. Try default port 502
5. Check firewall settings

**Debug**:
```bash
# Test connection
telnet wallbox_ip 502

# Check logs
grep -i "olife_wallbox" home-assistant.log
```

### Entities Unavailable

**Problem**: All entities show as unavailable

**Solutions**:
1. Check connection status
2. Verify slave ID matches Wallbox configuration
3. Check for error codes
4. Restart the integration

### Solar Optimization Not Working

**Problem**: Charging current not adjusting

**Solutions**:
1. Verify solar sensor entity ID
2. Check sensor reports positive values for export
3. Ensure minimum 6A threshold is met
4. Check charging phases configuration

## Advanced Topics

### Modbus Register Map

The integration uses these Modbus registers:

#### Global Configuration (5000-5026)
- 5003: Automatic charging
- 5006: Maximum station current
- 5008: LED PWM value

#### Connector A (2000-2026, 4000-4019)
- 2000: Error code
- 2004: EV state
- 4013: Total power
- 4006: Total energy

#### Connector B (2100-2126, 4100-4119)
- 2100: Error code (connector B)
- 2104: EV state (connector B)
- 4113: Total power (connector B)
- 4106: Total energy (connector B)

### Error Codes

Error codes are decoded as binary flags:
- Bit 0: RCD fault
- Bit 1: CP error
- Bit 2: Overcurrent
- Bit 3: Overvoltage
- Bit 4: Undervoltage
- Bit 5: Overtemperature
- Bit 6: Emergency stop
- Bit 7: Lock fault

### EV States

1. EV Unplugged
2. EV Connected
3. EV Verified
4. Charging
5. Charging Interrupted
6. Current Below 6A
7. Cloud Stopped
8. Tester Charging
9. RCD DC Sensor Fault
10. EVSE Error

## Development

### Architecture

The integration follows Home Assistant best practices:
- Uses DataUpdateCoordinator for efficient updates
- Implements proper entity lifecycle
- Supports device registry
- Provides comprehensive error handling

### Key Components

- `__init__.py` - Integration setup and coordinator
- `sensor.py` - All sensor entities
- `switch.py` - Switch entities
- `number.py` - Number input entities
- `button.py` - Button entities
- `modbus_client.py` - Modbus communication
- `solar_control.py` - Solar optimization logic
- `services.py` - Custom services

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Support

For issues and feature requests, please use the GitHub issue tracker.

## License

This integration is licensed under the MIT License. See LICENSE file for details.