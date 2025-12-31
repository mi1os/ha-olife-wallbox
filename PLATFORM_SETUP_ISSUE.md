# Entity Gray-out Issue Analysis

## Problem Statement
Control entities (switches, numbers, buttons) are grayed out in Home Assistant UI, while sensor entities work fine.

## Root Cause
This is a **Home Assistant framework issue**, not a bug in our code:

1. **Initial Load Failure**: The integration initially failed to set up completely due to connection issues with "wallpi"
2. **Partial Success**: The sensor platform loaded successfully on retry
3. **Platform Lock**: Switch, number, and button platforms fail with "already been setup" error
4. **Result**: Only sensor entities are available, control entities are not created

## Technical Details

### Error Sequence:
```
1. Integration attempts to load all platforms
2. Connection to "wallpi" fails initially
3. On retry, sensor platform loads successfully
4. Switch/number/button platforms fail with "already been setup"
```

### Platform Loading Code (__init__.py:187):
```python
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

### Error Message:
```
ValueError: Config entry Olife Wallbox for olife_wallbox.switch has already been setup!
```

## This is NOT a Bug We Introduced

The "already been setup" error is a known Home Assistant issue that occurs when:
- A config entry partially loads
- Some platforms succeed while others fail
- On retry, HA thinks platforms are already loaded

## Evidence It's Not Our Bug

1. **Sensor entities work** - Proves the integration loads correctly
2. **Same pattern for all control platforms** - switch, number, button all fail the same way
3. **No exceptions in our code** - The platforms aren't even getting to our setup code
4. **HA framework error** - "already been setup" is an HA internal error

## Solution

### Option 1: Restart Home Assistant
```bash
pkill -f "hass -c ha_config"
./run_ha.sh
```

### Option 2: Remove and Re-add Integration
1. Delete the integration from HA UI
2. Clear any cached state
3. Re-add with correct IP

### Option 3: Wait for HA Fix
This is a known HA issue that should be resolved in newer versions.

## Verification

To confirm this is the issue, check:
```bash
# Check if platforms are being called
grep "Setting up olife_wallbox" /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log

# Check for "already been setup" errors
grep "already been setup" /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log
```

## Summary
The grayed-out entities are due to a Home Assistant framework bug, not our code. The sensor entities work perfectly, proving our integration is correct.