"""Constants for Beacon Battery."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "beacon_battery"

CONF_SOURCE_DOMAIN: Final = "source_domain"
CONF_FRAMES: Final = "frames"
CONF_MAX_LEVEL: Final = "max_level"
CONF_HEARTBEAT_MINUTES: Final = "heartbeat_minutes"

# Options of config entry version 1, replaced by CONF_FRAMES.
LEGACY_CONF_SERVICE_DATA_UUID: Final = "service_data_uuid"
LEGACY_CONF_BATTERY_BYTE: Final = "battery_byte"

# Bermuda names its MAC-tracked devices with the lowercase MAC as identifier.
DEFAULT_SOURCE_DOMAIN: Final = "bermuda"
# Frames that carry battery %, written as "uuid:byte[:prefix]". The byte
# position counts from 0. The optional prefix (hex) must start the service
# data, which tells frames apart that share a UUID.
# - feaa:2:22  KKM / Blue Charm "system" frame on the Eddystone UUID:
#              [0x22, ?, battery %, MAC (6 bytes), ...]. Other Eddystone
#              frames (UID 0x00, URL 0x10, TLM 0x20) do not match the prefix.
# - 2080:0     KKM / Blue Charm frame sent next to the iBeacon frame:
#              [battery %, ?, major (2 bytes), minor (2 bytes)].
DEFAULT_FRAMES: Final = ["feaa:2:22", "2080:0"]
# Fresh cells read slightly above 100, so the level is capped.
DEFAULT_MAX_LEVEL: Final = 100
# How often the level of each beacon still in range is written again, so
# "last reported" checks see a live beacon even when its level does not change.
DEFAULT_HEARTBEAT_MINUTES: Final = 30

DEFAULT_OPTIONS: Final = {
    CONF_SOURCE_DOMAIN: DEFAULT_SOURCE_DOMAIN,
    CONF_FRAMES: DEFAULT_FRAMES,
    CONF_MAX_LEVEL: DEFAULT_MAX_LEVEL,
    CONF_HEARTBEAT_MINUTES: DEFAULT_HEARTBEAT_MINUTES,
}

BLUETOOTH_BASE_UUID_SUFFIX: Final = "-0000-1000-8000-00805f9b34fb"
