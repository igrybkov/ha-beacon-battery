"""Beacon Battery: battery sensors for BLE beacons, from their adverts.

The integration finds MAC-based devices of another integration (Bermuda by
default), listens for a service data frame that carries battery level, and adds
a battery sensor to each matching device.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]

type BeaconBatteryConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> bool:
    """Set up Beacon Battery from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: BeaconBatteryConfigEntry) -> None:
    """Reload so new options take effect."""
    await hass.config_entries.async_reload(entry.entry_id)
