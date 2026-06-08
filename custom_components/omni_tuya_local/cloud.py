from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .models import guess_device_type, guess_domain

_LOGGER = logging.getLogger(__name__)


async def async_fetch_cloud_devices(
    hass: HomeAssistant,
    api_key: str,
    api_secret: str,
    api_region: str,
    device_id: str = "",
) -> list[dict[str, Any]]:
    def _sync_fetch() -> list[dict[str, Any]]:
        import tinytuya

        cloud = tinytuya.Cloud(
            apiRegion=api_region,
            apiKey=api_key,
            apiSecret=api_secret,
            devId=device_id or None,
        )
        devices = cloud.getdevices()
        if isinstance(devices, list):
            return devices
        if isinstance(devices, dict):
            result = devices.get("result")
            if isinstance(result, list):
                return result
            _LOGGER.warning("Tuya Cloud returned unexpected payload: %s", devices)
        return []

    raw_devices = await hass.async_add_executor_job(_sync_fetch)
    formatted: list[dict[str, Any]] = []
    for raw in raw_devices:
        if not raw.get("id"):
            continue
        formatted.append({
            "device_id": raw.get("id"),
            "local_key": raw.get("key") or "",
            "host": raw.get("ip") or "",
            "ip": raw.get("ip") or "",
            "name": raw.get("name") or raw.get("id"),
            "version": str(raw.get("ver") or 3.3),
            "domain": guess_domain(raw),
            "device_type": guess_device_type(raw),
            "product_name": raw.get("product_name") or "",
            "category": raw.get("category") or "",
            "category_name": raw.get("category_name") or "",
            "product_id": raw.get("product_id") or "",
            "online": raw.get("online"),
            "gateway_id": raw.get("gateway_id") or "",
            "node_id": raw.get("node_id") or "",
            "sub": raw.get("sub", False),
            "raw": raw,
        })
    return formatted
