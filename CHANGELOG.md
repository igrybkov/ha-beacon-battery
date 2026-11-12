# Changelog

## 0.2.0

- Reads the KKM / Blue Charm "System" frame (`0xFEAA`, starting with `0x22`) as well as `0x2080`. A beacon whose System slot is on, or that just got a new battery, gets its sensor too.
- New option **Battery frames** replaces **Service data UUID** and **Battery byte position**. Existing settings are migrated.
- Home Assistant keeps frames a beacon stopped sending in its merged advert data. The frame that changed most recently is read now, and when several change at once the lowest level wins. A stale frame no longer hides the live one.

## 0.1.1

- Fix: setup failed with "too many values to unpack" when any device in Home Assistant had a three-part identifier. Only two-part identifiers with a string value are read now.

## 0.1.0

- Adds a battery sensor to each MAC-based Bermuda device whose beacon sends a battery frame. No MAC list needed.
- Reads the level from service data `0x2080` (KKM / Blue Charm beacons), byte 0, capped at 100. UUID, byte, cap and source integration are options.
- Uses Home Assistant's Bluetooth stack, so every adapter and ESPHome proxy feeds it.
- Writes on change, and every 30 minutes for beacons still in range, so Battery Notes "not reported" checks work.
- Keeps the last level across restarts.
