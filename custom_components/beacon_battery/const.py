"""Constants for Beacon Battery."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "beacon_battery"

CONF_SOURCE_DOMAIN: Final = "source_domain"
CONF_SERVICE_DATA_UUID: Final = "service_data_uuid"
CONF_BATTERY_BYTE: Final = "battery_byte"
CONF_MAX_LEVEL: Final = "max_level"
CONF_HEARTBEAT_MINUTES: Final = "heartbeat_minutes"

# Bermuda names its MAC-tracked devices with the lowercase MAC as identifier.
DEFAULT_SOURCE_DOMAIN: Final = "bermuda"
# KKM / Blue Charm beacons send battery % in service data 0x2080 next to the
# iBeacon frame: [battery %, ?, major (2 bytes), minor (2 bytes)].
DEFAULT_SERVICE_DATA_UUID: Final = "00002080-0000-1000-8000-00805f9b34fb"
DEFAULT_BATTERY_BYTE: Final = 0
# Fresh cells read slightly above 100, so the level is capped.
DEFAULT_MAX_LEVEL: Final = 100
# Write the same value again at most this often, so "last reported" checks
# see a live beacon even when its level does not change.
DEFAULT_HEARTBEAT_MINUTES: Final = 30

DEFAULT_OPTIONS: Final = {
    CONF_SOURCE_DOMAIN: DEFAULT_SOURCE_DOMAIN,
    CONF_SERVICE_DATA_UUID: DEFAULT_SERVICE_DATA_UUID,
    CONF_BATTERY_BYTE: DEFAULT_BATTERY_BYTE,
    CONF_MAX_LEVEL: DEFAULT_MAX_LEVEL,
    CONF_HEARTBEAT_MINUTES: DEFAULT_HEARTBEAT_MINUTES,
}

BLUETOOTH_BASE_UUID_SUFFIX: Final = "-0000-1000-8000-00805f9b34fb"
