# Entity Availability Issue Analysis

## Problem
The entities in Home Assistant UI are grayed out and cannot be used, even though read-only mode is disabled.

## Root Cause
This is the **expected behavior** when the Wallbox device is unreachable:

1. All entities initialize with `_available = False`
2. They only become available after a successful `async_update()` call
3. The `async_update()` method tries to read from Modbus registers
4. Since the connection to "wallpi" fails, the entities remain unavailable
5. Home Assistant grays out unavailable entities to indicate they're not functional

## Code Flow

### Number Entity (number.py line 80):
```python
self._available = False  # Initially unavailable
```

### In async_update() (number.py line 203):
```python
if result is not None:
    self._available = True  # Only if Modbus read succeeds
```

### Modbus Connection Issue
The integration is configured to connect to "wallpi:5432" which doesn't exist in your network, so all Modbus reads fail.

## Solution

### For Testing Without Hardware:
1. The entities **should** be grayed out when no device is connected
2. This prevents users from trying to control a non-existent device
3. This is the correct behavior in Home Assistant

### To Test Entity Functionality:
1. Configure the integration with a valid IP address (even if no device exists)
2. The entities will still be grayed out (correct behavior)
3. But you can verify they were created properly

### Verification Steps:
```bash
# Check if entities were created
grep "Creating" /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log | grep olife

# Check entity states
grep "unavailable" /Users/mv/mvsrc/ha-olife/ha_config/home-assistant.log | grep olife
```

## This is Not a Bug
The grayed-out entities indicate proper error handling - when the device is unreachable, Home Assistant correctly disables the controls to prevent user confusion.

## With Real Hardware
When connected to an actual Wallbox:
1. Modbus connection succeeds
2. `async_update()` reads valid data
3. Entities become available (`_available = True`)
4. Controls become active and usable

The current behavior is correct and prevents users from trying to control a disconnected device.