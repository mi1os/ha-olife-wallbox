"""Modbus client for Olife Energy Wallbox."""
import logging
import asyncio
from datetime import datetime, timedelta
import socket
import time
from typing import Optional, List, Union

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ExceptionResponse

_LOGGER = logging.getLogger(__name__)

# Constants for retry logic
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
CONNECTION_TIMEOUT = 10  # seconds

# Modbus exception codes mapped to human-readable messages
MODBUS_EXCEPTIONS = {
    1: "Illegal Function",
    2: "Illegal Data Address",
    3: "Illegal Data Value",
    4: "Slave Device Failure",
    5: "Acknowledge",
    6: "Slave Device Busy",
    7: "Negative Acknowledge",
    8: "Memory Parity Error",
    10: "Gateway Path Unavailable",
    11: "Gateway Target Device Failed to Respond"
}

class OlifeWallboxModbusClient:
    """Modbus client for Olife Energy Wallbox."""

    def __init__(self, host, port, slave_id):
        """Initialize the Modbus client."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        
        # Initialize with minimal parameters
        self._client = ModbusTcpClient(
            host=host, 
            port=port,
            timeout=CONNECTION_TIMEOUT
        )
        
        # Set the slave ID directly as an attribute - this pattern works on most versions
        self._client.unit_id = slave_id
        
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_connect_attempt = datetime.min
        self._connection_errors = 0
        self._consecutive_errors = 0
        self._last_successful_connection = datetime.min

    async def connect(self):
        """Connect to the Modbus device with retry logic."""
        if self._connected:
            return True

        # Implement backoff for repeated connection failures
        now = datetime.now()
        backoff_time = min(10 * (2 ** min(self._connection_errors, 5)), 300)  # Max 5 minutes
        
        if now - self._last_connect_attempt < timedelta(seconds=backoff_time):
            _LOGGER.debug(
                "Waiting %s seconds before next connection attempt to %s:%s",
                backoff_time, self._host, self._port
            )
            return False

        self._last_connect_attempt = now

        try:
            _LOGGER.debug("Connecting to Olife Wallbox at %s:%s", self._host, self._port)
            async with self._lock:
                connected = await asyncio.get_event_loop().run_in_executor(
                    None, self._client.connect
                )
                
                if connected:
                    self._connected = True
                    self._connection_errors = 0
                    self._consecutive_errors = 0
                    self._last_successful_connection = now
                    _LOGGER.info("Successfully connected to Olife Wallbox at %s:%s", self._host, self._port)
                else:
                    self._connection_errors += 1
                    _LOGGER.warning(
                        "Connection attempt to Olife Wallbox at %s:%s failed (attempt %s)",
                        self._host, self._port, self._connection_errors
                    )
                    self._connected = False
                
                return connected
        except ConnectionException as ex:
            self._connection_errors += 1
            self._connected = False
            _LOGGER.error(
                "Failed to connect to Olife Wallbox at %s:%s: %s (attempt %s)",
                self._host, self._port, ex, self._connection_errors
            )
            return False
        except (socket.timeout, socket.error) as ex:
            self._connection_errors += 1
            self._connected = False
            _LOGGER.error(
                "Socket error connecting to Olife Wallbox at %s:%s: %s (attempt %s)",
                self._host, self._port, ex, self._connection_errors
            )
            return False
        except Exception as ex:
            self._connection_errors += 1
            self._connected = False
            _LOGGER.error(
                "Unexpected error connecting to Olife Wallbox at %s:%s: %s (attempt %s)",
                self._host, self._port, ex, self._connection_errors
            )
            return False

    async def disconnect(self):
        """Disconnect from the Modbus device."""
        if not self._connected:
            return

        try:
            _LOGGER.debug("Disconnecting from Olife Wallbox at %s:%s", self._host, self._port)
            async with self._lock:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._client.close
                )
                _LOGGER.debug("Successfully disconnected from Olife Wallbox")
        except ConnectionException as ex:
            _LOGGER.error("Error disconnecting from Olife Wallbox: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error disconnecting from Olife Wallbox: %s", ex)
        finally:
            self._connected = False

    async def read_holding_registers(self, address, count) -> Optional[List[int]]:
        """Read holding registers with retry mechanism."""
        for retry in range(MAX_RETRIES):
            if not await self.connect():
                if retry < MAX_RETRIES - 1:
                    _LOGGER.debug(
                        "Connection failed, retrying in %s seconds (attempt %s/%s)",
                        RETRY_DELAY, retry + 1, MAX_RETRIES
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None

            try:
                async with self._lock:
                    # Start timing the request
                    start_time = time.time()
                    
                    # Use a compatibility layer for different pymodbus versions
                    try:
                        # Try newer API pattern
                        result = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: self._client.read_holding_registers(address, count=count)
                        )
                    except TypeError:
                        try:
                            # Try older API pattern
                            result = await asyncio.get_event_loop().run_in_executor(
                                None, 
                                lambda: self._client.read_holding_registers(address, count)
                            )
                        except Exception as e:
                            _LOGGER.error("Failed to read registers: %s", e)
                            return None
                    
                    # Log request time for performance monitoring
                    elapsed = time.time() - start_time
                    _LOGGER.debug(
                        "Read register %s (count: %s) completed in %.3f seconds",
                        address, count, elapsed
                    )
                    
                    # Reset consecutive errors on success
                    self._consecutive_errors = 0
                    
                    # Handle different types of errors
                    if isinstance(result, ExceptionResponse):
                        exception_code = result.exception_code
                        exception_msg = MODBUS_EXCEPTIONS.get(
                            exception_code, f"Unknown exception code: {exception_code}"
                        )
                        _LOGGER.error(
                            "Modbus exception reading register %s: %s", 
                            address, exception_msg
                        )
                        return None
                    
                    if hasattr(result, 'isError') and result.isError():
                        _LOGGER.error("Error reading register %s: %s", address, result)
                        return None
                    
                    if not hasattr(result, 'registers'):
                        _LOGGER.error(
                            "Unexpected response format reading register %s: %s", 
                            address, result
                        )
                        return None
                        
                    return result.registers
            except (ConnectionException, ModbusException) as ex:
                self._consecutive_errors += 1
                self._connected = False
                
                if retry < MAX_RETRIES - 1:
                    _LOGGER.warning(
                        "Error reading register %s: %s. Retrying in %s seconds (attempt %s/%s)",
                        address, ex, RETRY_DELAY, retry + 1, MAX_RETRIES
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    _LOGGER.error(
                        "Failed to read register %s after %s attempts: %s",
                        address, MAX_RETRIES, ex
                    )
                    return None
            except asyncio.CancelledError:
                _LOGGER.debug("Read operation cancelled for register %s", address)
                raise  # Re-raise cancellation to properly handle it
            except Exception as ex:
                self._consecutive_errors += 1
                self._connected = False
                _LOGGER.error(
                    "Unexpected error reading register %s: %s",
                    address, ex
                )
                if retry < MAX_RETRIES - 1:
                    _LOGGER.warning("Retrying in %s seconds", RETRY_DELAY)
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    return None
                    
        # If we get here, all retries failed
        return None

    async def write_register(self, address, value) -> bool:
        """Write to a holding register with retry mechanism.
        
        Note: This method uses Function Code 6 (0x06) - Write Single Register.
        If your device requires Function Code 16 (0x10), use write_registers instead.
        """
        # Redirect to write_registers which uses Function Code 16 (0x10)
        return await self.write_registers(address, [value])
        
    async def write_registers(self, address, values) -> bool:
        """Write to holding registers with retry mechanism using Function Code 16 (0x10).
        
        This method uses Function Code 16 (Preset Multiple Registers) as required by some Modbus devices.
        """
        for retry in range(MAX_RETRIES):
            if not await self.connect():
                if retry < MAX_RETRIES - 1:
                    _LOGGER.debug(
                        "Connection failed, retrying in %s seconds (attempt %s/%s)",
                        RETRY_DELAY, retry + 1, MAX_RETRIES
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return False

            try:
                async with self._lock:
                    # Log the write operation
                    _LOGGER.debug(
                        "Writing values %s to registers starting at %s", 
                        values, address
                    )
                    
                    # Start timing the request
                    start_time = time.time()
                    
                    # Use a compatibility layer for different pymodbus versions
                    try:
                        # Try newer API pattern first
                        _LOGGER.debug("Attempting to write values %s to register %s using newer API pattern (Function Code 16)", values, address)
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self._client.write_registers(address, values=values)
                        )
                    except TypeError as te:
                        _LOGGER.debug("TypeError with newer API pattern: %s. Trying older pattern.", te)
                        try:
                            # Try older API pattern
                            result = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: self._client.write_registers(address, values)
                            )
                        except Exception as e:
                            _LOGGER.error("Failed to write registers with older API pattern: %s", e)
                            return False
                    except Exception as e:
                        _LOGGER.error("Failed to write registers with newer API pattern: %s", e)
                        return False
                    
                    # Log request time for performance monitoring
                    elapsed = time.time() - start_time
                    _LOGGER.debug(
                        "Write to registers starting at %s completed in %.3f seconds",
                        address, elapsed
                    )
                    
                    # Reset consecutive errors on success
                    self._consecutive_errors = 0
                    
                    # Handle different types of errors
                    if isinstance(result, ExceptionResponse):
                        exception_code = result.exception_code
                        exception_msg = MODBUS_EXCEPTIONS.get(
                            exception_code, f"Unknown exception code: {exception_code}"
                        )
                        _LOGGER.error(
                            "Modbus exception writing to registers starting at %s: %s", 
                            address, exception_msg
                        )
                        return False
                    
                    if hasattr(result, 'isError') and result.isError():
                        _LOGGER.error("Error writing to registers starting at %s: %s", address, result)
                        return False
                    
                    _LOGGER.debug(
                        "Successfully wrote values %s to registers starting at %s",
                        values, address
                    )
                    return True
            except (ConnectionException, ModbusException) as ex:
                self._consecutive_errors += 1
                self._connected = False
                
                if retry < MAX_RETRIES - 1:
                    _LOGGER.warning(
                        "Error writing to registers starting at %s: %s. Retrying in %s seconds (attempt %s/%s)",
                        address, ex, RETRY_DELAY, retry + 1, MAX_RETRIES
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    _LOGGER.error(
                        "Failed to write to registers starting at %s after %s attempts: %s",
                        address, MAX_RETRIES, ex
                    )
                    return False
            except asyncio.CancelledError:
                _LOGGER.debug("Write operation cancelled for registers starting at %s", address)
                raise  # Re-raise cancellation to properly handle it
            except Exception as ex:
                self._consecutive_errors += 1
                self._connected = False
                _LOGGER.error(
                    "Unexpected error writing to registers starting at %s: %s",
                    address, ex
                )
                if retry < MAX_RETRIES - 1:
                    _LOGGER.warning("Retrying in %s seconds", RETRY_DELAY)
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    return False
                    
        # If we get here, all retries failed
        return False
        
    @property
    def connection_errors(self) -> int:
        """Return the number of connection errors."""
        return self._connection_errors
        
    @property
    def consecutive_errors(self) -> int:
        """Return the number of consecutive errors."""
        return self._consecutive_errors
        
    @property
    def last_successful_connection(self) -> datetime:
        """Return the timestamp of the last successful connection."""
        return self._last_successful_connection 