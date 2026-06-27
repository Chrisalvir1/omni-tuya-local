from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .models import guess_device_type, guess_domain
from .pet_feeder import function_id

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
            result = devices
        elif isinstance(devices, dict):
            # Detectar error de autenticación / permisos de la API Tuya
            if not devices.get("success", True):
                code = devices.get("code", "?")
                msg = devices.get("msg", "unknown")
                _LOGGER.error(
                    "Tuya Cloud API error — code: %s, msg: %s. "
                    "Verifica: Access ID, Access Secret, región del proyecto "
                    "y que la cuenta de la app esté vinculada al proyecto IoT.",
                    code, msg,
                )
                raise ValueError(f"Tuya Cloud error {code}: {msg}")
            result = devices.get("result")
            if not isinstance(result, list):
                _LOGGER.warning("Tuya Cloud returned unexpected payload: %s", devices)
                return []
        else:
            return []

        # Product functions are the authoritative way to resolve the wildly
        # different DP ids used by Tuya pet feeders.  A failed schema lookup is
        # non-fatal: LAN control and existing mappings continue to work.
        for device in result:
            device_id = device.get("id")
            if not device_id or guess_device_type(device) != "pet_feeder":
                continue
            try:
                functions = cloud.getfunctions(device_id)
                if isinstance(functions, dict):
                    functions = functions.get("result", functions.get("functions", []))
                if isinstance(functions, list):
                    device["_omni_tuya_functions"] = functions
            except Exception as err:
                _LOGGER.debug("Could not fetch Tuya functions for %s: %s", device_id, err)
        return result

    raw_devices = await hass.async_add_executor_job(_sync_fetch)
    formatted: list[dict[str, Any]] = []
    for raw in raw_devices:
        if not raw.get("id"):
            continue
        functions = raw.get("_omni_tuya_functions") or []
        feeder_mapping = _pet_feeder_mapping(functions)
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
            "tuya_functions": functions,
            **feeder_mapping,
        })
    return formatted


def _pet_feeder_mapping(functions: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive only safe pet-feeder controls from Tuya's product schema."""
    mapping: dict[str, Any] = {}
    for function in functions:
        if not isinstance(function, dict):
            continue
        dp_id = function_id(function)
        code = str(function.get("code") or function.get("identifier") or "").lower()
        if not dp_id:
            continue
        if code in ("feed_publish", "manual_feed"):
            mapping["pet_feeder_feed_dp"] = dp_id
            mapping["pet_feeder_feed_kind"] = "value"
        elif code == "quick_feed" and "pet_feeder_feed_dp" not in mapping:
            mapping["pet_feeder_feed_dp"] = dp_id
            mapping["pet_feeder_feed_kind"] = "bool"
        elif "clean" in code and any(word in code for word in ("hopper", "food", "feed", "empty")):
            mapping["pet_feeder_clean_hopper_dp"] = dp_id
            mapping["pet_feeder_clean_hopper_value"] = True
    return mapping
