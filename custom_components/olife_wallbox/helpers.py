"""Helper functions for Olife Wallbox integration."""
from __future__ import annotations

from typing import Tuple

DEVICE_ID_DELIMITER = "_"


class DeviceUniqueIdError(ValueError):
    """Raised when a stored Olife device unique_id cannot be parsed."""


def format_device_unique_id(host: str, port: int, slave_id: int) -> str:
    """Return a normalized unique_id string for registry storage."""
    return f"{host}{DEVICE_ID_DELIMITER}{port}{DEVICE_ID_DELIMITER}{slave_id}"


def parse_device_unique_id(unique_id: str) -> Tuple[str, int, int]:
    """Validate and split Olife unique_id into host, port, slave_id."""
    if not unique_id or DEVICE_ID_DELIMITER not in unique_id:
        raise DeviceUniqueIdError(f"Missing delimiter in '{unique_id}'")
    parts = unique_id.split(DEVICE_ID_DELIMITER)
    if len(parts) != 3:
        raise DeviceUniqueIdError(f"Expected 3 parts, got {len(parts)} in '{unique_id}'")
    host, port_raw, slave_raw = (part.strip() for part in parts)
    if not host:
        raise DeviceUniqueIdError("Host segment empty")
    try:
        port = int(port_raw)
        slave_id = int(slave_raw)
    except ValueError as exc:
        raise DeviceUniqueIdError(f"Non-integer port/slave in '{unique_id}'") from exc
    return host, port, slave_id