# Changelog

## 0.1.1

- Fix: setup failed with "too many values to unpack" when any device in Home Assistant had a three-part identifier. Only two-part identifiers with a string value are read now.

## 0.1.0

- Adds a battery sensor to each MAC-based Bermuda device whose beacon sends a battery frame. No MAC list needed.
- Reads the level from service data `0x2080` (KKM / Blue Charm beacons), byte 0, capped at 100. UUID, byte, cap and source integration are options.
- Uses Home Assistant's Bluetooth stack, so every adapter and ESPHome proxy feeds it.
- Writes on change, and every 30 minutes for beacons still in range, so Battery Notes "not reported" checks work.
- Keeps the last level across restarts.
