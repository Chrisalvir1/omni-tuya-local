# Omni Tuya Local v1.12.2

Adds the admin-only `omni_tuya_local/camera_webrtc` Home Assistant WebSocket command used by Matter All-in-One 2.3.8 for supported Tuya cameras. It obtains the real device audio capabilities and a one-session MQTT signaling configuration using the existing Cloud region and credentials. The response is transient; secrets are not written to storage or logs.

Validation covers capability gating, safe errors, the real Home Assistant WebSocket decorators, and successful live Cloud allocation on the configured Frienhund feeder. Actual speaker audibility still requires an in-person check after the add-on update.
