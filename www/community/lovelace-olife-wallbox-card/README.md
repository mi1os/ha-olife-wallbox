# Olife Wallbox Card

A custom Lovelace card for Home Assistant that provides a beautiful dashboard for monitoring and controlling your Olife Energy Wallbox EV charging station.

![Olife Wallbox Card](https://raw.githubusercontent.com/mi1os/ha-olife-wallbox/main/www/community/lovelace-olife-wallbox-card/card-preview.png)

## Features

- Beautiful, modern UI specifically designed for Olife Wallbox users
- Status indicators showing charging state, power usage, and energy consumption
- Interactive controls for starting/stopping charging and adjusting current limits
- Fully customizable to show only the information you need

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Frontend
   - Click on the three dots in the top right corner
   - Select "Custom repositories"
   - Add `https://github.com/mi1os/ha-olife-wallbox` with category "Lovelace"
3. Search for "Olife Wallbox Card" in the Frontend tab and install it

### Manual Installation

1. Download the `olife-wallbox-card.js` file from the latest release
2. Copy the file to your Home Assistant config in the `www/community/lovelace-olife-wallbox-card/` folder (create the folders if they don't exist)
3. Add the card as a resource in your Lovelace configuration:
   - Go to Configuration → Lovelace Dashboards → Resources
   - Add `/local/community/lovelace-olife-wallbox-card/olife-wallbox-card.js` as a JavaScript module

## Usage

### Adding the Card

1. Go to your dashboard and click "Edit Dashboard"
2. Click the "+" button to add a new card
3. Search for "Olife Wallbox Card" and select it
4. Configure the card settings

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | Olife Wallbox | Title displayed at the top of the card |
| `entity` | string | *Required* | Primary entity (usually the charging switch or EV state sensor) |
| `power_entity` | string | Optional | Entity ID for power consumption (usually `sensor.olife_wallbox_charge_power`) |
| `energy_entity` | string | Optional | Entity ID for energy consumption (e.g., `sensor.olife_wallbox_daily_charge_energy`) |
| `current_limit_entity` | string | Optional | Entity ID for current limit adjustment (usually `number.olife_wallbox_current_limit`) |
| `show_stats` | boolean | true | Whether to show the statistics section |
| `show_controls` | boolean | true | Whether to show the controls section |
| `theme` | string | default | Card theme (when Home Assistant themes are supported) |

### Example Configuration

```yaml
type: custom:olife-wallbox-card
title: My Wallbox
entity: switch.olife_wallbox_charging
power_entity: sensor.olife_wallbox_charge_power
energy_entity: sensor.olife_wallbox_daily_charge_energy
current_limit_entity: number.olife_wallbox_current_limit
show_stats: true
show_controls: true
```

## Troubleshooting

If the card doesn't appear:
1. Check that the resource has been added correctly
2. Ensure the entities you've configured exist and are available
3. Check the browser console for any JavaScript errors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. 