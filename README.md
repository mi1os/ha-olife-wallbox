# Olife Energy Wallbox Integration for Home Assistant

This custom integration allows you to monitor and control your Olife Energy Wallbox charging station in Home Assistant, with comprehensive support for all Modbus registers.

## Features

- **Real-time Monitoring**: Detailed status monitoring with human-readable state descriptions
- **Multi-phase Support**: Individual current, voltage, power, and energy readings for each phase
- **Comprehensive Energy Tracking**: Daily, monthly, and yearly energy statistics
- **Error Diagnostic Tools**: Detailed error reporting with binary flag decoding
- **Control Pilot Monitoring**: Track the communication state between your charger and vehicle
- **Energy Dashboard Integration**: Full support for Home Assistant Energy Dashboard
- **Robust Error Handling**: Automatic retries, backoff strategies, and detailed logging
- **Custom Services**: Control all aspects of your charging station via services
- **Automation Triggers**: Create automations based on charging events

## Installation

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Go to HACS > Integrations > "+" button > "Custom repositories"
3. Add the URL: `https://github.com/yourusername/olife_wallbox`
4. Select "Integration" as category
5. Search for "Olife Energy Wallbox" and install

### Manual Installation

1. Download the latest release
2. Unzip and copy the `olife_wallbox` folder into your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services > Add Integration
2. Search for "Olife Energy Wallbox"
3. Enter the IP address and other required configuration details

## Available Sensors

### Status Sensors
- **EV State**: Human-readable vehicle state with descriptive icons
- **CP State**: Control Pilot signal state with detailed status information
- **Error Code**: Comprehensive error reporting with binary flag decoding

### Per-Phase Measurements
- **Phase 1/2/3 Current**: Current draw on each phase (A)
- **Phase 1/2/3 Voltage**: Voltage level on each phase (V)
- **Phase 1/2/3 Power**: Power consumption on each phase (W)
- **Phase 1/2/3 Energy**: Energy consumption on each phase (kWh)

### Energy Tracking
- **Current Session Energy**: Energy consumed in the current charging session (Wh)
- **Total Station Energy**: Lifetime energy consumption (Wh)
- **Daily Charge Energy**: Energy consumed today, resets at midnight (Wh)
- **Monthly Charge Energy**: Energy consumed this month, resets on the 1st (Wh) 
- **Yearly Charge Energy**: Energy consumed this year, resets on January 1st (kWh)

### Other Sensors
- **Charge Current**: Current charging rate (A)
- **Charge Power**: Current charging power (W)
- **Maximum Station Current**: Maximum allowable charging current (A)
- **Current Limit**: Currently set charging current limit (A)
- **LED PWM**: LED brightness level (0-1000)

## Available Controls

- **Charging Switch**: Enable/disable charging
- **Verify User Switch**: Control user verification
- **Automatic Mode Switch**: Toggle automatic mode
- **Current Limit**: Set the charging current limit (0-32A)
- **Maximum Station Current**: Set the maximum station current (0-63A)
- **LED Brightness**: Set the LED brightness (0-1000)
- **Charging Mode**: Select charging mode (Fast, Solar, Spot, Off)

## Available Services

This integration provides the following services:

- `olife_wallbox.start_charge`: Start charging
- `olife_wallbox.stop_charge`: Stop charging
- `olife_wallbox.set_current_limit`: Set the charging current limit (0-32A)
- `olife_wallbox.set_max_current`: Set the maximum allowed charging current (0-63A)
- `olife_wallbox.set_led_brightness`: Set the LED brightness level (0-1000)
- `olife_wallbox.reset_energy_counters`: Reset energy counters (daily, monthly, or yearly)

## Automation Triggers

The integration provides the following device triggers for automations:

- **EV Connected**: Triggered when an EV is connected to the charging station
- **EV Disconnected**: Triggered when an EV is disconnected from the charging station
- **Charging Started**: Triggered when charging begins
- **Charging Stopped**: Triggered when charging ends
- **User Authenticated**: Triggered on successful user authentication
- **Error**: Triggered when an error occurs

## Energy Dashboard Integration

This integration fully supports the Home Assistant Energy Dashboard. All energy sensors are properly configured with the correct device classes and state classes for automatic integration.

## Troubleshooting

The integration supports Home Assistant diagnostics, which can help with troubleshooting. To access diagnostics:

1. Go to Settings > Devices & Services
2. Click on the "Olife Energy Wallbox" integration
3. Click on "Download Diagnostics"

The diagnostics report includes:
- Device information
- Connection status
- Entity status
- Error counts
- Configuration details

## Modbus Register Support

This integration has been developed with the official Olife Energy Wallbox Modbus register specification. It supports the following register categories:

- EVSE-A <2000-2026> registers
- INTERNAL WATTMETER <4000-4019> registers
- CONFIG <5000-5026> registers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 