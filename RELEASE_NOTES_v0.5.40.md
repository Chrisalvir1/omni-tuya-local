# Omni Tuya Local v0.5.40

- Added safe LAN DPS discovery for every device.
- Persists observed DPS schema so discovered entities survive restarts and temporary outages.
- Exposes unknown numeric/text DPS as read-only sensors and boolean DPS as read-only binary sensors.
- Uses Tuya product-function metadata to label discovered DPS when the cloud provides it.
- Does not guess unknown writable DPS as controls, protecting device settings from unsafe commands.
