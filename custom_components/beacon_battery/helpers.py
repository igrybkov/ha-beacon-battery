"""Pure helpers for Beacon Battery. No Home Assistant state here."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .const import BLUETOOTH_BASE_UUID_SUFFIX

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
_SHORT_UUID_RE = re.compile(r"^(0x)?[0-9a-f]{4}$")
_FULL_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def normalize_mac(value: str) -> str | None:
    """Return the MAC in lowercase colon form, or None if it is not a MAC."""
    mac = value.strip().lower().replace("-", ":")
    return mac if _MAC_RE.match(mac) else None


def normalize_service_data_uuid(value: str) -> str | None:
    """Expand a 16-bit UUID such as "2080" or "0x2080" to the full 128-bit form.

    Returns None when the value is not a valid UUID.
    """
    uuid = value.strip().lower()
    if _SHORT_UUID_RE.match(uuid):
        return f"0000{uuid[-4:]}{BLUETOOTH_BASE_UUID_SUFFIX}"
    return uuid if _FULL_UUID_RE.match(uuid) else None


def mac_identifiers(
    identifiers: Iterable[tuple[Any, ...]], source_domain: str
) -> dict[str, tuple[str, str]]:
    """Map each MAC identifier of the source integration to the identifier itself.

    Identifiers that are not MACs (for example iBeacon UUID based ones) are
    skipped, since adverts only carry the MAC. Other integrations store
    identifiers of other shapes (three parts, non-string values), so only a
    two-part identifier with a string value is read.
    """
    found: dict[str, tuple[str, str]] = {}
    for identifier in identifiers:
        if len(identifier) != 2:
            continue
        domain, value = identifier
        if domain != source_domain or not isinstance(value, str):
            continue
        if mac := normalize_mac(value):
            found[mac] = (domain, value)
    return found


@dataclass(frozen=True, slots=True)
class Frame:
    """A service data frame that carries the battery level in one byte."""

    uuid: str
    byte_index: int
    prefix: bytes = b""

    def payload(self, service_data: Mapping[str, bytes]) -> bytes | None:
        """Return this frame's service data, or None if it is absent or another frame."""
        data = service_data.get(self.uuid)
        if data is None or not data.startswith(self.prefix) or len(data) <= self.byte_index:
            return None
        return data

    def level(self, payload: bytes, max_level: int) -> int:
        """Read the level from this frame's payload, capped at max_level."""
        return min(payload[self.byte_index], max_level)


def parse_frame(spec: str) -> Frame | None:
    """Parse "uuid:byte[:prefix]", for example "2080:0" or "feaa:2:22".

    The UUID may be 16-bit or full 128-bit. Returns None when the spec is invalid.
    """
    parts = spec.strip().lower().split(":")
    if len(parts) not in (2, 3):
        return None
    uuid = normalize_service_data_uuid(parts[0])
    if uuid is None or not parts[1].isdigit():
        return None
    prefix_hex = parts[2].removeprefix("0x") if len(parts) == 3 else ""
    try:
        prefix = bytes.fromhex(prefix_hex)
    except ValueError:
        return None
    if len(parts) == 3 and not prefix:
        return None
    return Frame(uuid, int(parts[1]), prefix)


def format_frame(frame: Frame) -> str:
    """Write a frame back as a spec, with a 16-bit UUID in short form."""
    uuid = frame.uuid
    if uuid.startswith("0000") and uuid.endswith(BLUETOOTH_BASE_UUID_SUFFIX):
        uuid = uuid[4:8]
    spec = f"{uuid}:{frame.byte_index}"
    return f"{spec}:{frame.prefix.hex()}" if frame.prefix else spec


class FrameChooser:
    """Pick which frame to read for each beacon.

    The Bluetooth stack merges service data across adverts, so a frame the
    beacon stopped sending stays in the merged data until the beacon goes out
    of range. A fixed order could then keep reading a dead frame. Instead the
    frame whose payload changed most recently wins. When several change at
    once (the first advert seen, for example after a restart), the lowest
    level wins: a battery only drains, so a stale frame reads higher than a
    live one. List order breaks a tie.
    """

    def __init__(self, frames: list[Frame], max_level: int) -> None:
        """Initialize with frames in fallback order."""
        self._frames = frames
        self._max_level = max_level
        self._last: dict[str, dict[int, bytes]] = {}
        self._preferred: dict[str, int] = {}

    @property
    def uuids(self) -> list[str]:
        """Distinct service data UUIDs of all frames, in order."""
        return list(dict.fromkeys(frame.uuid for frame in self._frames))

    def level(self, mac: str, service_data: Mapping[str, bytes], *, track: bool) -> int | None:
        """Return the level for a beacon.

        With track, payload changes update which frame is preferred. Without
        it (a periodic re-read of unchanged data), the current choice is used.
        """
        payloads = [frame.payload(service_data) for frame in self._frames]
        if track:
            last = self._last.setdefault(mac, {})
            changed = [
                index
                for index, payload in enumerate(payloads)
                if payload is not None and last.get(index) != payload
            ]
            for index in changed:
                last[index] = payloads[index]  # type: ignore[assignment]
            if changed:
                self._preferred[mac] = min(
                    changed,
                    key=lambda index: (
                        self._frames[index].level(payloads[index], self._max_level),  # type: ignore[arg-type]
                        index,
                    ),
                )
        preferred = self._preferred.get(mac)
        if preferred is not None and (payload := payloads[preferred]) is not None:
            return self._frames[preferred].level(payload, self._max_level)
        for frame, payload in zip(self._frames, payloads, strict=True):
            if payload is not None:
                return frame.level(payload, self._max_level)
        return None
