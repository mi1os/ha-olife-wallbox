"""Modbus client for Olife Energy Wallbox."""
import logging
import asyncio
from datetime import datetime, timedelta

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

_LOGGER = logging.getLogger(__name__)

class OlifeWallboxModbusClient:
    """Modbus client for Olife Energy Wallbox."""

    def __init__(self, host, port, slave_id):
        """Initialize the Modbus client."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client = ModbusTcpClient(host=host, port=port)
        self._client.unit_id = slave_id  # Set the unit_id/slave_id during initialization
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_connect_attempt = datetime.min

    async def connect(self):
        """Connect to the Modbus device."""
        if self._connected:
            return True

        # Limit connection attempts
        now = datetime.now()
        if now - self._last_connect_attempt < timedelta(seconds=10):
            return False

        self._last_connect_attempt = now

        try:
            async with self._lock:
                connected = await asyncio.get_event_loop().run_in_executor(
                    None, self._client.connect
                )
                self._connected = connected
                return connected
        except ConnectionException as ex:
            _LOGGER.error("Failed to connect to Olife Wallbox: %s", ex)
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the Modbus device."""
        if not self._connected:
            return

        try:
            async with self._lock:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._client.close
                )
        except ConnectionException as ex:
            _LOGGER.error("Error disconnecting from Olife Wallbox: %s", ex)
        finally:
            self._connected = False

    async def read_holding_registers(self, address, count):
        """Read holding registers."""
        if not await self.connect():
            return None

        try:
            async with self._lock:
                # Ensure unit_id is set before each request
                self._client.unit_id = self._slave_id
                # Use named parameters for compatibility
                result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self._client.read_holding_registers(address=address, count=count)
                )
                
                if hasattr(result, 'isError') and result.isError():
                    _LOGGER.error("Error reading register %s: %s", address, result)
                    return None
                    
                return result.registers
        except (ConnectionException, ModbusException) as ex:
            _LOGGER.error("Error reading register %s: %s", address, ex)
            self._connected = False
            return None
        except Exception as ex:
            _LOGGER.error("Unexpected error reading register %s: %s", address, ex)
            self._connected = False
            return None

    async def write_register(self, address, value):
        """Write to a holding register."""
        if not await self.connect():
            return False

        try:
            async with self._lock:
                # Ensure unit_id is set before each request
                self._client.unit_id = self._slave_id
                # Use named parameters for compatibility
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.write_register(address=address, value=value)
                )
                
                if hasattr(result, 'isError') and result.isError():
                    _LOGGER.error("Error writing to register %s: %s", address, result)
                    return False
                    
                return True
        except (ConnectionException, ModbusException) as ex:
            _LOGGER.error("Error writing to register %s: %s", address, ex)
            self._connected = False
            return False
        except Exception as ex:
            _LOGGER.error("Unexpected error writing to register %s: %s", address, ex)
            self._connected = False
            return False 