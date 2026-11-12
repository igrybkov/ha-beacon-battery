"""Battery sensors for BLE beacons, attached to the source integration's devices."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import BeaconBatteryConfigEntry
from .const import (
    CONF_FRAMES,
    CONF_HEARTBEAT_MINUTES,
    CONF_MAX_LEVEL,
    CONF_SOURCE_DOMAIN,
    DEFAULT_OPTIONS,
)
from .helpers import FrameChooser, mac_identifiers, normalize_mac, parse_frame

_LOGGER = logging.getLogger(__name__)

UNIQUE_ID_SUFFIX = "_battery"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BeaconBatteryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up battery sensors."""
    tracker = BeaconTracker(hass, entry, async_add_entities)
    tracker.async_start()


class BeaconTracker:
    """Match adverts to source devices and keep one battery sensor per device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BeaconBatteryConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
    ) -> None:
        """Initialize the tracker."""
        options: dict[str, Any] = {**DEFAULT_OPTIONS, **entry.options}
        self._hass = hass
        self._entry = entry
        self._add_entities = async_add_entities
        self._source_domain: str = options[CONF_SOURCE_DOMAIN]
        frames = [frame for spec in options[CONF_FRAMES] if (frame := parse_frame(spec))]
        self._chooser = FrameChooser(frames, int(options[CONF_MAX_LEVEL]))
        self._heartbeat = timedelta(minutes=int(options[CONF_HEARTBEAT_MINUTES]))
        # MAC -> device ID of the source device
        self._devices: dict[str, str] = {}
        self._entities: dict[str, BeaconBatterySensor] = {}

    @callback
    def async_start(self) -> None:
        """Load devices, restore known sensors and start listening."""
        self._async_refresh_devices()
        self._async_restore_entities()
        self._entry.async_on_unload(
            self._hass.bus.async_listen(
                dr.EVENT_DEVICE_REGISTRY_UPDATED, self._async_device_registry_updated
            )
        )
        # Beacons send non-connectable adverts. The matcher defaults to
        # connectable only, so it must be turned off explicitly.
        for uuid in self._chooser.uuids:
            self._entry.async_on_unload(
                bluetooth.async_register_callback(
                    self._hass,
                    self._async_on_advert,
                    {"service_data_uuid": uuid, "connectable": False},
                    bluetooth.BluetoothScanningMode.PASSIVE,
                )
            )
        # The Bluetooth stack drops adverts whose payload did not change, so
        # the callback above only sees changes. A timer reports the level of
        # every beacon that is still present, so "last reported" stays fresh.
        self._entry.async_on_unload(
            async_track_time_interval(self._hass, self._async_heartbeat, self._heartbeat)
        )

    @callback
    def _async_refresh_devices(self) -> None:
        """Rebuild the MAC map from the device registry."""
        devices: dict[str, str] = {}
        for device in dr.async_get(self._hass).devices:
            if device.disabled:
                continue
            for mac in mac_identifiers(device.identifiers, self._source_domain):
                devices[mac] = device.id
        self._devices = devices

    @callback
    def _async_device_registry_updated(self, _event: Event) -> None:
        """Pick up devices the source integration adds or removes later."""
        self._async_refresh_devices()

    @callback
    def _async_restore_entities(self) -> None:
        """Re-create sensors from earlier runs so they keep their last value."""
        restored = []
        for reg_entry in er.async_entries_for_config_entry(
            er.async_get(self._hass), self._entry.entry_id
        ):
            if not reg_entry.unique_id.endswith(UNIQUE_ID_SUFFIX):
                continue
            mac = reg_entry.unique_id.removesuffix(UNIQUE_ID_SUFFIX)
            if (device := self._device(mac)) is None:
                continue
            entity = BeaconBatterySensor(mac, device, None)
            self._entities[mac] = entity
            restored.append(entity)
        if restored:
            self._add_entities(restored)

    @callback
    def _device(self, mac: str) -> dr.DeviceEntry | None:
        """Return the source device for a MAC, if there is one."""
        if (device_id := self._devices.get(mac)) is None:
            return None
        return dr.async_get(self._hass).async_get(device_id)

    @callback
    def _async_on_advert(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle an advert that carries the battery frame."""
        mac = normalize_mac(service_info.address)
        if mac is None or (device := self._device(mac)) is None:
            return
        level = self._chooser.level(mac, service_info.service_data, track=True)
        if level is None:
            return
        if (entity := self._entities.get(mac)) is None:
            _LOGGER.debug("Adding battery sensor for %s (%s%%)", mac, level)
            entity = BeaconBatterySensor(mac, device, level)
            self._entities[mac] = entity
            self._add_entities([entity])
            return
        entity.async_set_level(level, force=False)

    @callback
    def _async_heartbeat(self, _now: datetime) -> None:
        """Write the level again for each beacon that is still in range."""
        for mac, entity in self._entities.items():
            address = mac.upper()
            if not bluetooth.async_address_present(self._hass, address, connectable=False):
                continue
            info = bluetooth.async_last_service_info(self._hass, address, connectable=False)
            if info is None:
                continue
            level = self._chooser.level(mac, info.service_data, track=False)
            if level is not None:
                entity.async_set_level(level, force=True)


class BeaconBatterySensor(RestoreSensor):
    """Battery level of one beacon."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        mac: str,
        device: dr.DeviceEntry,
        level: int | None,
    ) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{mac}{UNIQUE_ID_SUFFIX}"
        # Show the sensor on the source device. A device belongs to one config
        # entry, so device_info would create a second device instead.
        self.device_entry = device
        self._attr_native_value = level

    async def async_added_to_hass(self) -> None:
        """Restore the last level when no advert has arrived yet."""
        await super().async_added_to_hass()
        if self._attr_native_value is None and (last := await self.async_get_last_sensor_data()):
            self._attr_native_value = last.native_value

    @callback
    def async_set_level(self, level: int, *, force: bool) -> None:
        """Store a level. Write it when it changed, or always when forced."""
        changed = level != self._attr_native_value
        self._attr_native_value = level
        if self.hass is None:
            # Not added yet; the value is written when it is.
            return
        if changed or force:
            self.async_write_ha_state()
