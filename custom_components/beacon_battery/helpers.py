"""Pure helpers for Beacon Battery. No Home Assistant state here."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

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
    identifiers: Iterable[tuple[str, str]], source_domain: str
) -> dict[str, tuple[str, str]]:
    """Map each MAC identifier of the source integration to the identifier itself.

    Identifiers that are not MACs (for example iBeacon UUID based ones) are
    skipped, since adverts only carry the MAC.
    """
    found: dict[str, tuple[str, str]] = {}
    for domain, value in identifiers:
        if domain != source_domain:
            continue
        if mac := normalize_mac(value):
            found[mac] = (domain, value)
    return found


def parse_battery(
    service_data: Mapping[str, bytes], uuid: str, byte_index: int, max_level: int
) -> int | None:
    """Read the battery level from service data, capped at max_level."""
    payload = service_data.get(uuid)
    if payload is None or len(payload) <= byte_index:
        return None
    return min(payload[byte_index], max_level)
