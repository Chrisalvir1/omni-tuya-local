# Omni Tuya Local v1.11.3

Omni adds video entities for supported Tuya IPC cameras, including compatible video feeders such as the Smart Video Feeder.

## Tuya camera video

- Home Assistant gets a native `camera` entity for supported Tuya video products.
- Each still-image or stream request asks Tuya Cloud for a fresh, temporary RTSP URL.
- Every new stream session, including a HomeKit session, receives a newly allocated URL. Home Assistant keeps an active stream worker alive, so if Tuya expires its URL during a long session, close/reopen the stream to allocate a current URL. DPS sensors continue independently over LAN.
- The camera can be exported through HomeKit Bridge in Accessory mode; HomeKit Secure Video is not supported.
- DPS status and device commands continue to use Omni's LAN connection. The live video URL comes from Tuya's cloud video service.
- The Tuya IoT project must have access to **IoT Video Live Stream**, and the device firmware must support stream allocation. Tuya may charge for forwarded RTSP/HLS traffic.
- Signed stream URLs are not persisted or logged.

## Verification

- Unit tests cover RTSP allocation, failed/invalid responses, missing cloud credentials, and camera identification for a video feeder versus an ordinary plug.
- Live playback still depends on Tuya granting the project's stream API permission and returning a playable URL for the specific device.
