"""Modbus client for Olife Energy Wallbox."""
import logging
import asyncio
from asyncio import wait_for, TimeoutError as AsyncioTimeoutError
from datetime import datetime, timedelta
import socket
import time
from typing import Optional, List, Union

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse

from .const import (
    REG_LED_PWM,
    REG_MAX_STATION_CURRENT
)

_LOGGER = logging.getLogger(__name__)

# Constants for retry logic
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
CONNECTION_TIMEOUT = 10  # seconds
EXECUTOR_TIMEOUT = 15.0  # seconds for executor operations

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
        self._client = None
        self._create_client()
        
        self._lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()
        self._connected = False
        self._last_connect_attempt = datetime.min
        self._connection_errors = 0
        self._consecutive_errors = 0
        self._last_successful_connection = datetime.min
        self._register_cache = {}

    def _create_client(self):
        """Create a fresh client, closing any existing one.

        Must be called while holding the I/O lock so the socket on the shared
        client is never swapped out from under a concurrent Modbus operation.
        """
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = ModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=CONNECTION_TIMEOUT
        )
        self._client.unit_id = self._slave_id

    def _reset_client(self):
        """Close and drop the current client so it cannot be reused.

        Must be called while holding the I/O lock. Marks the connection dead;
        the next operation will create a fresh client via connect().
        """
        self._connected = False
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
    def _in_backoff_window(self) -> bool:
        """Return True if a connection-level backoff is currently active.

        Mirrors the backoff math in connect(): while this is True, connect()
        refuses to attempt a reconnect, so per-register retries cannot make
        progress and should fail fast.
        """
        if self._connection_errors == 0:
            return False
        backoff_time = min(2 * (2 ** min(self._connection_errors, 6)), 120)
        return datetime.now() - self._last_connect_attempt < timedelta(seconds=backoff_time)

    async def connect(self):
        """Connect to the Modbus device with retry logic."""
        if self._connected and self._client is not None:
            if await self._check_connection():
                return True
            else:
                _LOGGER.debug("Connection check failed, reconnecting")

        now = datetime.now()
        backoff_time = min(2 * (2 ** min(self._connection_errors, 6)), 120)

        if now - self._last_connect_attempt < timedelta(seconds=backoff_time):
            return False

        self._last_connect_attempt = now
        if not hasattr(self, '_successful_connections_count'):
            self._successful_connections_count = 0

        try:
            async with self._connection_lock:
                if self._connected and self._client is not None:
                    if await self._check_connection():
                        return True

                async with self._lock:
                    # Always start a fresh client/socket under the I/O lock so we
                    # never replace the socket while another op is in flight.
                    self._create_client()
                    client = self._client

                    connected = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(None, client.connect),
                        timeout=EXECUTOR_TIMEOUT
                    )

                    if connected and client.socket:
                        had_previous_errors = self._connection_errors > 0

                        self._connected = True
                        self._connection_errors = 0
                        self._consecutive_errors = 0
                        self._last_successful_connection = now
                        self._successful_connections_count += 1

                        if (self._successful_connections_count == 1 or
                            had_previous_errors or
                            self._successful_connections_count % 100 == 0):
                            _LOGGER.info("Successfully connected to Olife Wallbox at %s:%s", self._host, self._port)
                    else:
                        self._connection_errors += 1
                        _LOGGER.warning(
                            "Connection attempt to Olife Wallbox at %s:%s failed (attempt %s)",
                            self._host, self._port, self._connection_errors
                        )
                        self._reset_client()

                    return connected
        except (AsyncioTimeoutError, ConnectionException, socket.timeout, socket.error) as ex:
            self._connection_errors += 1
            async with self._lock:
                self._reset_client()
            _LOGGER.error(
                "Connection error to Olife Wallbox at %s:%s: %s (attempt %s)",
                self._host, self._port, type(ex).__name__, self._connection_errors
            )
            return False
        except Exception as ex:
            self._connection_errors += 1
            async with self._lock:
                self._reset_client()
            _LOGGER.error("Unexpected error connecting: %s", ex)
            return False
    async def disconnect(self):
        """Disconnect from the Modbus device.

        Always closes the underlying client/socket if one exists, even when
        ``_connected`` is already False, so a stale socket is never leaked
        (e.g. after a failed transaction marked the connection dead).
        """
        try:
            _LOGGER.debug("Disconnecting from Olife Wallbox at %s:%s", self._host, self._port)
            async with self._connection_lock:
                async with self._lock:
                    if self._client is not None:
                        await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, self._client.close), timeout=5.0)
                        _LOGGER.debug("Successfully disconnected from Olife Wallbox")
        except ConnectionException as ex:
            _LOGGER.error("Error disconnecting from Olife Wallbox: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error disconnecting from Olife Wallbox: %s", ex)
        finally:
            self._connected = False

    async def read_holding_registers(self, address, count) -> Optional[List[int]]:
        """Read holding registers with retry mechanism."""
        # Add a small cache for frequently accessed registers
        cache_key = f"{address}_{count}"
        if hasattr(self, '_register_cache') and cache_key in self._register_cache:
            cache_entry = self._register_cache[cache_key]
            # Only use cache for certain registers and if the cache is fresh (< 10 seconds old)
            if address in [REG_LED_PWM, REG_MAX_STATION_CURRENT] and \
               (datetime.now() - cache_entry['timestamp']).total_seconds() < 10:
                return cache_entry['value']
        
        for retry in range(MAX_RETRIES):
            if not await self.connect():
                # During an active connection-level backoff window connect()
                # returns False immediately; fail fast and let the coordinator
                # make a single reconnect decision next cycle instead of
                # burning per-register retries against a dead socket.
                if self._in_backoff_window():
                    _LOGGER.debug(
                        "Connection in backoff window, skipping read of register %s", address
                    )
                    return None
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

                    # Bind the executor call to a local client reference so a
                    # later retry cannot race a second op through self._client.
                    client = self._client
                    try:
                        result = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, lambda: client.read_holding_registers(address, count=count)), timeout=EXECUTOR_TIMEOUT)
                    except AsyncioTimeoutError:
                        # The blocking pymodbus call may still be running in the
                        # executor thread on `client`; abandon that client so the
                        # timed-out op cannot be reused concurrently on retry.
                        self._consecutive_errors += 1
                        self._reset_client()
                        _LOGGER.warning("Timed out reading register %s; resetting connection", address)
                        if retry < MAX_RETRIES - 1:
                            continue
                        return None

                    # Log request time for performance monitoring
                    elapsed = time.time() - start_time
                    
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
                    
                    # Log the register values in decimal and hex format
                    register_values = result.registers
                    hex_values = [f"0x{val:04X}" for val in register_values]
                    _LOGGER.debug(
                        "Read register %s (count: %s) completed in %.3f seconds. Values: %s (hex: %s)",
                        address, count, elapsed, register_values, hex_values
                    )
                    
                    # Reset consecutive errors on success
                    self._consecutive_errors = 0
                    
                    # Cache the result for specific registers
                    if address in [REG_LED_PWM, REG_MAX_STATION_CURRENT]:
                        if not hasattr(self, '_register_cache'):
                            self._register_cache = {}
                        self._register_cache[cache_key] = {
                            'timestamp': datetime.now(),
                            'value': register_values
                        }
                    
                    return register_values
            except (AsyncioTimeoutError, ConnectionException, ModbusException) as ex:
                self._consecutive_errors += 1
                # Close the dead socket so it is not leaked / reused.
                async with self._lock:
                    self._reset_client()

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
                async with self._lock:
                    self._reset_client()
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
        # Guard against values outside the 16-bit register range (0..65535).
        for value in values:
            if not isinstance(value, int) or value < 0 or value > 0xFFFF:
                _LOGGER.error(
                    "Refusing to write out-of-range value %s to registers starting at %s (must be 0..65535)",
                    value, address
                )
                return False

        for retry in range(MAX_RETRIES):
            if not await self.connect():
                # Fail fast during an active backoff window (see read path).
                if self._in_backoff_window():
                    _LOGGER.debug(
                        "Connection in backoff window, skipping write to register %s", address
                    )
                    return False
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

                    # Bind the executor call to a local client reference so a
                    # later retry cannot race a second op through self._client.
                    client = self._client
                    _LOGGER.debug("Attempting to write values %s to register %s (Function Code 16)", values, address)
                    try:
                        result = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, lambda: client.write_registers(address, values=values)), timeout=EXECUTOR_TIMEOUT)
                    except AsyncioTimeoutError:
                        # The blocking pymodbus call may still be running in the
                        # executor thread on `client`; abandon that client so the
                        # timed-out op cannot be reused concurrently on retry.
                        self._consecutive_errors += 1
                        self._reset_client()
                        _LOGGER.warning("Timed out writing register %s; resetting connection", address)
                        if retry < MAX_RETRIES - 1:
                            continue
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
            except (AsyncioTimeoutError, ConnectionException, ModbusException) as ex:
                self._consecutive_errors += 1
                # Close the dead socket so it is not leaked / reused.
                async with self._lock:
                    self._reset_client()

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
                async with self._lock:
                    self._reset_client()
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

    async def _check_connection(self) -> bool:
        """Check if the connection is still alive without reconnecting.

        Uses a short timeout to avoid blocking other operations.
        """
        if not self._connected or self._client is None:
            return False

        # Check socket is still open
        if not self._client.socket:
            return False

        now = datetime.now()
        if now - self._last_successful_connection > timedelta(minutes=5):
            _LOGGER.debug("Connection may be stale, performing verification")
            try:
                # Serialize the verification read under the I/O lock so it cannot
                # interleave Modbus frames with the coordinator/entity reads.
                async with self._lock:
                    client = self._client
                    if client is None:
                        return False
                    # Use a short timeout (5s) to avoid blocking other entities
                    result = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(
                            None, lambda: client.read_holding_registers(2104, count=1)
                        ),
                        timeout=5.0,
                    )
                if result is None or (hasattr(result, 'isError') and result.isError()):
                    _LOGGER.debug("Connection check failed: invalid response")
                    return False
                self._last_successful_connection = now
                return True
            except Exception as ex:
                _LOGGER.debug("Connection check failed: %s", ex)
                return False

        return True