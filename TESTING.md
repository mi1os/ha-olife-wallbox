# Testing Olife Energy Wallbox Integration

This document provides instructions for testing the Olife Energy Wallbox integration in Home Assistant.

## Prerequisites

1. Home Assistant development environment set up
2. The integration code in `/custom_components/olife_wallbox/`
3. Optional: Actual Olife Wallbox hardware for real testing

## Common Testing Issues

### Issue: "Failed to connect to device" Error

**Symptom**: The integration fails to set up with connection errors in logs.

**Cause**: There's likely an existing configuration with invalid connection details.

**Solution**:
1. Stop Home Assistant: `pkill -f "hass -c ha_config"`
2. Remove the existing configuration:
   ```bash
   # Edit the config entries file
   nano /Users/mv/mvsrc/ha-olife/ha_config/.storage/core.config_entries

   # Find and remove the olife_wallbox entry (search for "olife_wallbox")
   # Or delete the entire file to reset all configurations
   rm /Users/mv/mvsrc/ha-olife/ha_config/.storage/core.config_entries
   ```
3. Restart Home Assistant: `./run_ha.sh`
4. Add the integration again through the UI

### Issue: Integration Not Loading

**Symptom**: The integration doesn't appear in Home Assistant.

**Solution**:
1. Check that the symlink exists:
   ```bash
   ls -la /Users/mv/mvsrc/ha-olife/ha_config/custom_components/
   ```
2. If missing, create it:
   ```bash
   ln -s ../../custom_components/olife_wallbox /Users/mv/mvsrc/ha-olife/ha_config/custom_components/olife_wallbox
   ```

## Testing Without Hardware

### 1. Basic Integration Test
```bash
# Start Home Assistant
./run_ha.sh

# Check logs for errors
tail -f /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log | grep -E "(ERROR|olife_wallbox)"
```

### 2. Add Integration via UI
1. Open http://localhost:8123
2. Go to Settings > Devices & Services
3. Click "Add Integration"
4. Search for "Olife Energy Wallbox"
5. Enter test values:
   - Host: `192.168.1.100` (or any valid IP format)
   - Port: `502`
   - Slave ID: `1`
   - Name: `Test Wallbox`

### 3. Verify Entity Creation
Check that these entities are created (they'll show as unavailable without real hardware):
- `sensor.test_wallbox_ev_state`
- `sensor.test_wallbox_charge_power`
- `switch.test_wallbox_charging`
- `number.test_wallbox_current_limit`

### 4. Test Services
In Developer Tools > Services, test these services:
- `olife_wallbox.start_charge`
- `olife_wallbox.stop_charge`
- `olife_wallbox.set_current_limit`

## Testing With Hardware

### 1. Connect to Real Device
1. Find your Wallbox IP address (check your router)
2. Ensure Modbus TCP is enabled on the Wallbox
3. Default port is 502
4. Default slave ID is 1

### 2. Enable Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.olife_wallbox: debug
```

### 3. Test All Features
1. **Basic Operations**:
   - Start/stop charging
   - Adjust current limit
   - Check EV state changes

2. **Multi-phase Support**:
   - Verify phase sensors are created
   - Check voltage/current readings

3. **Energy Tracking**:
   - Monitor daily/monthly/yearly energy
   - Test energy dashboard integration

4. **Error Handling**:
   - Disconnect network cable
   - Test error recovery
   - Check error sensors

5. **Solar Optimization**:
   - Configure solar power entity
   - Test automatic current adjustment

## Automated Testing

### Run Unit Tests
```bash
# If tests exist
python -m pytest tests/

# Or test specific modules
python -m pytest tests/test_olife_wallbox.py
```

### Code Quality Checks
```bash
# Run linting
flake8 custom_components/olife_wallbox/

# Check imports
python -m py_compile custom_components/olife_wallbox/__init__.py
```

## Debugging Tips

### 1. Check Connection
```bash
# Test Modbus connection
python -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('192.168.1.100', port=502); print(c.connect())"
```

### 2. View Raw Logs
```bash
# See full logs
tail -n 1000 /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log | grep -A5 -B5 "olife_wallbox"
```

### 3. Reset Everything
```bash
# Stop HA
pkill -f "hass -c ha_config"

# Clear all data
rm -rf /Users/mv/mvsrc/ha-olife/ha_config/.storage/
rm /Users/mv/mvsrc/ha-olife/ha_config/home-assistant_v2.db

# Start fresh
./run_ha.sh
```

## Testing Checklist

- [ ] Integration loads without errors
- [ ] All entities are created
- [ ] Services are registered
- [ ] Configuration flow works
- [ ] Read-only mode functions
- [ ] Multi-connector detection works
- [ ] Error handling is robust
- [ ] Memory leaks are prevented
- [ ] All 19 MV issues are resolved

## Performance Testing

Monitor these metrics:
- CPU usage during polling
- Memory consumption over time
- Network traffic frequency
- Error recovery time

## Known Limitations

1. Without hardware, entities show as unavailable
2. Some services may timeout without device response
3. Energy calculations require real data
4. Solar optimization needs actual solar sensor

## Reporting Issues

When reporting issues, include:
1. Home Assistant version
2. Integration version (from manifest.json)
3. Full error logs
4. Steps to reproduce
5. Expected vs actual behavior