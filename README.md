# Olife Energy Wallbox Integration for Home Assistant

This custom integration allows you to monitor and control your Olife Energy Wallbox charging station in Home Assistant.

## Features

- Real-time monitoring of charging station status and energy usage
- Energy tracking with daily, monthly, and yearly statistics
- Full Home Assistant Energy Dashboard integration
- Custom services for controlling the charging station
- Diagnostics support for troubleshooting

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

## Available Services

This integration provides the following services:

- `olife_wallbox.start_charge`: Start charging
- `olife_wallbox.stop_charge`: Stop charging
- `olife_wallbox.set_current_limit`: Set the charging current limit for the current session
- `olife_wallbox.set_max_current`: Set the maximum allowed charging current
- `olife_wallbox.set_led_brightness`: Set the LED brightness level
- `olife_wallbox.reset_energy_counters`: Reset energy counters (daily, monthly, or yearly)

## Energy Dashboard Integration

This integration fully supports the Home Assistant Energy dashboard. The following sensors are available for energy monitoring:

- `sensor.olife_wallbox_session_energy`: Energy consumption for the current session
- `sensor.olife_wallbox_total_energy`: Total lifetime energy consumption
- `sensor.olife_wallbox_daily_energy`: Energy consumed today (resets at midnight)
- `sensor.olife_wallbox_monthly_energy`: Energy consumed this month (resets on the 1st of each month)
- `sensor.olife_wallbox_yearly_energy`: Energy consumed this year (resets on January 1st)

## Troubleshooting

The integration supports Home Assistant diagnostics, which can help with troubleshooting. To access diagnostics:

1. Go to Settings > Devices & Services
2. Click on the "Olife Energy Wallbox" integration
3. Click on "Download Diagnostics"

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 