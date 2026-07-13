# Omni Tuya Local v0.5.38

- Added a visible **Sync Tuya Cloud** action to the Add Integration flow.
- New Smart Life devices are imported as Home Assistant config entries and existing metadata is refreshed.
- Cloud metadata now refreshes automatically every six hours; local control remains LAN-only.
- Fixed shared storage races and restart overwrites that could lose updated device data.
- Removed the virtual Omni Tuya hub device from physical-device lists.
