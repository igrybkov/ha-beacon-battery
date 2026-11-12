"""Beacon Battery: battery sensors for BLE beacons, from their adverts.

The integration finds MAC-based devices of another integration (Bermuda by
default), listens for a service data frame that carries battery level, and adds
a battery sensor to each matching device.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FRAMES,
    DEFAULT_FRAMES,
    LEGACY_CONF_BATTERY_BYTE,
    LEGACY_CONF_SERVICE_DATA_UUID,
)
from .helpers import Frame, format_frame, normalize_service_data_uuid

PLATFORMS: list[Platform] = [Platform.SENSOR]

type BeaconBatteryConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> bool:
    """Set up Beacon Battery from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> bool:
    """Migrate options from older config entry versions."""
    if entry.version > 2:
        # Written by a newer release; this one cannot read it.
        return False
    if entry.version == 1:
        options = dict(entry.options)
        uuid = normalize_service_data_uuid(str(options.pop(LEGACY_CONF_SERVICE_DATA_UUID, "")))
        byte_index = int(options.pop(LEGACY_CONF_BATTERY_BYTE, 0))
        frames = list(DEFAULT_FRAMES)
        if uuid is not None:
            legacy = format_frame(Frame(uuid, byte_index))
            if legacy not in frames:
                # A custom frame from version 1 keeps first place.
                frames.insert(0, legacy)
        options[CONF_FRAMES] = frames
        hass.config_entries.async_update_entry(entry, options=options, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> None:
    """Reload so new options take effect."""
    await hass.config_entries.async_reload(entry.entry_id)
