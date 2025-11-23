#!/bin/bash

# Clean up Python cache to avoid stale bytecode issues
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Stop any running Home Assistant instance
pkill -f "hass -c ha_config" 2>/dev/null || true
sleep 1

# Start Home Assistant
source ha_venv/bin/activate
hass -c ha_config