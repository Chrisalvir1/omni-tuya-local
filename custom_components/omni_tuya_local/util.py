from __future__ import annotations

from .const import TUYA_BRIGHTNESS_MAX, TUYA_BRIGHTNESS_MIN


def tuya_to_ha_brightness(tuya_value: int) -> int:
    normalized = (int(tuya_value) - TUYA_BRIGHTNESS_MIN) / (TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN)
    return max(0, min(255, int(normalized * 255)))


def ha_to_tuya_brightness(ha_value: int) -> int:
    normalized = int(ha_value) / 255
    return max(TUYA_BRIGHTNESS_MIN, min(TUYA_BRIGHTNESS_MAX, int(normalized * TUYA_BRIGHTNESS_MAX)))


def parse_physical_id(device_id: str) -> tuple[str, int]:
    if "_" in device_id:
        base, maybe_dps = device_id.rsplit("_", 1)
        try:
            return base, int(maybe_dps)
        except ValueError:
            return device_id, 1
    return device_id, 1


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
