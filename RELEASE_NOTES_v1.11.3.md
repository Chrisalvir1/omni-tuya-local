# Omni Tuya Local v1.11.3

Omni adds video entities for supported Tuya IPC cameras, including compatible video feeders such as the Smart Video Feeder.

## Tuya camera video

- Home Assistant gets a native `camera` entity for supported Tuya video products.
- Still-image requests and creation of a Home Assistant stream worker request a temporary RTSP URL from Tuya Cloud. Signed URLs are never persisted or logged.
- Camera entities can feed HomeKit Bridge or Matter All-in-One Chrisalvir Camera.UI for HAP. HA reuses a camera stream worker and its original URL; after Tuya expires or changes that URL, reload the Omni config entry to allocate a new one. Automatic cross-session refresh between HA and HAP is not implemented yet.
- DPS sensors continue to update over LAN, independently of the video stream.
- DPS status and device commands continue to use Omni's LAN connection. The live video URL comes from Tuya's cloud video service.
- The Tuya IoT project must have access to **IoT Video Live Stream**, and the device firmware must support stream allocation. Tuya may charge for forwarded RTSP/HLS traffic.
- Signed stream URLs are not persisted or logged.

## Verification

- Unit tests cover RTSP allocation, failed/invalid responses, missing cloud credentials, and camera identification for a video feeder versus an ordinary plug.
- Live playback still depends on Tuya granting the project's stream API permission and returning a playable URL for the specific device.
