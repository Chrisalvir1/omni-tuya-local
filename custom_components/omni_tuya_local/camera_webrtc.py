"""Transient Tuya WebRTC bootstrap. Never log or persist session secrets."""
from __future__ import annotations

import secrets
from typing import Any


class CameraWebRtcError(ValueError):
    """Public, credential-free failure."""


def allocate_webrtc(client: Any, device_id: str) -> dict[str, Any]:
    """Use the same Cloud region/account as RTSP, with one MQTT identity per call."""
    def request(path: str, **kwargs: Any) -> dict[str, Any]:
        response = client.cloudrequest(path, **kwargs)
        if not isinstance(response, dict) or response.get("success") is not True:
            code = response.get("code") if isinstance(response, dict) else None
            safe_code = str(code) if str(code).isdigit() else "unknown"
            raise CameraWebRtcError(f"Tuya WebRTC request failed (code {safe_code})")
        result = response.get("result")
        if not isinstance(result, dict):
            raise CameraWebRtcError("Tuya WebRTC response is incomplete")
        return result

    config = request(f"/v1.0/devices/{device_id}/webrtc-configs")
    attributes = config.get("audio_attributes") or {}
    modes = attributes.get("call_mode", [])
    hardware = attributes.get("hardware_capability", [])
    if config.get("supports_webrtc") is not True or 2 not in modes or 2 not in hardware:
        raise CameraWebRtcError("Tuya does not advertise two-way audio for this session")
    device = request(f"/v1.0/devices/{device_id}")
    uid = device.get("uid")
    if not isinstance(uid, str) or not uid:
        raise CameraWebRtcError("Tuya user identity is unavailable")
    mqtt = request("/v1.0/open-hub/access/config", action="POST", post={
        "uid": uid, "link_id": secrets.token_hex(4), "link_type": "mqtt", "topics": "ipc",
    })
    topic = (mqtt.get("source_topic") or {}).get("ipc", "")
    if not (isinstance(topic, str) and topic.startswith("/av/u/") and config.get("auth") and config.get("moto_id") and (mqtt.get("sink_topic") or {}).get("ipc")):
        raise CameraWebRtcError("Tuya signaling configuration is incomplete")
    return {"deviceId": device_id, "auth": config["auth"], "motoId": config["moto_id"],
            "iceServers": (config.get("p2p_config") or {}).get("ices", []),
            "audioAttributes": attributes, "skill": config.get("skill"), "mqtt": mqtt}


async def async_allocate_webrtc(hass: Any, cloud: dict[str, Any], device_id: str) -> dict[str, Any]:
    def allocate() -> dict[str, Any]:
        import tinytuya
        try:
            client = tinytuya.Cloud(apiRegion=cloud.get("region", "eu"), apiKey=cloud.get("api_key", ""),
                                    apiSecret=cloud.get("api_secret", ""), apiDeviceID=device_id)
            return allocate_webrtc(client, device_id)
        except CameraWebRtcError:
            raise
        except Exception:
            raise CameraWebRtcError("Tuya WebRTC bootstrap failed") from None
    return await hass.async_add_executor_job(allocate)
