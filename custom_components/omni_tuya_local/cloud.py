from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .models import guess_device_type, guess_domain
from .pet_feeder import function_id

_LOGGER = logging.getLogger(__name__)


class TuyaCloudError(ValueError):
    """An API error safe to show to the Home Assistant administrator."""


def normalize_mac(value: Any) -> str:
    """Return a MAC in a comparable form, or an empty string if invalid."""
    compact = "".join(char for char in str(value or "").lower() if char in "0123456789abcdef")
    return compact if len(compact) == 12 else ""


def find_cloud_device_by_mac(devices: list[dict[str, Any]], mac: str) -> dict[str, Any] | None:
    """Find a cloud device regardless of MAC punctuation or casing."""
    wanted = normalize_mac(mac)
    if not wanted:
        return None
    for device in devices:
        raw = device.get("raw") or {}
        candidates = (device.get("mac"), raw.get("mac"), raw.get("mac_address"))
        if any(normalize_mac(candidate) == wanted for candidate in candidates):
            return device
    return None


async def async_fetch_cloud_devices(
    hass: HomeAssistant,
    api_key: str,
    api_secret: str,
    api_region: str,
    device_id: str = "",
) -> list[dict[str, Any]]:
    api_key = str(api_key or "").strip()
    api_secret = str(api_secret or "").strip()
    api_region = str(api_region or "").strip().lower()
    device_id = str(device_id or "").strip()

    def _sync_fetch() -> list[dict[str, Any]]:
        import tinytuya

        _LOGGER.info(
            "Conectando a Tuya Cloud (region=%s, apiKey=%s..., device_id=%s)",
            api_region,
            api_key[:6] if len(api_key) >= 6 else "***",
            device_id or "ninguno",
        )

        def _error_detail(payload: Any) -> str:
            """Normalize TinyTuya's error response formats and provide actionable guidance."""
            if not isinstance(payload, dict):
                return type(payload).__name__
            err_msg = ""
            if "Error" in payload:
                err_msg = str(payload["Error"])
            elif "Err" in payload:
                err_msg = str(payload["Err"])
            elif "Payload" in payload:
                err_msg = str(payload["Payload"])
            else:
                code = payload.get("code", "?")
                msg = payload.get("msg", "unknown")
                err_msg = f"{code}: {msg}"

            if "28841107" in err_msg or "data center is suspended" in err_msg.lower():
                return (
                    f"{err_msg} -> [Causa: El Data Center del proyecto en Tuya IoT Platform está suspendido "
                    "o el periodo de prueba de la API IoT Core expiró. Ve a iot.tuya.com -> Cloud -> Development "
                    "-> Project -> Data Center / Cloud Services para reactivarlo o renovar la prueba gratuita]"
                )
            return err_msg

        def _is_error(payload: Any) -> bool:
            return isinstance(payload, dict) and (
                "Error" in payload or "Err" in payload or not payload.get("success", True)
            )

        def _cloud_with_id(initial_device_id: str | None):
            return tinytuya.Cloud(
                apiRegion=api_region,
                apiKey=api_key,
                apiSecret=api_secret,
                # TinyTuya expects apiDeviceID.  Passing the historical
                # ``devId`` spelling is silently accepted but ignored.
                apiDeviceID=initial_device_id,
            )

        cloud = _cloud_with_id(device_id or None)
        devices = None

        # Si device_id es un UID de usuario (o varios separados por coma, ej. eu1621898281305Wo1vo)
        if device_id and any(device_id.startswith(pfx) for pfx in ("eu", "us", "cn", "in", "az", "ay")):
            uids = [u.strip() for u in device_id.split(",") if u.strip()]
            all_user_devs = []
            for uid in uids:
                req = cloud.cloudrequest(f"/v1.0/users/{uid}/devices")
                if isinstance(req, dict) and isinstance(req.get("result"), list):
                    all_user_devs.extend(req["result"])
            if all_user_devs:
                devices = all_user_devs

        if devices is None:
            devices = cloud.getdevices()
        _LOGGER.info("Respuesta de Tuya Cloud getdevices(): %s", type(devices).__name__)
        # A virtual ID can be stale, belong to another Tuya project, or be
        # unavailable to this API client.  Try the project-wide device lookup
        # before failing the whole sync; it works for linked Smart Life
        # accounts that expose their devices directly to the IoT project.
        if device_id and _is_error(devices):
            first_error = _error_detail(devices)
            _LOGGER.warning(
                "Tuya lookup with configured virtual ID failed (%s); retrying without it",
                first_error,
            )
            fallback_cloud = _cloud_with_id(None)
            fallback_devices = fallback_cloud.getdevices()
            if isinstance(fallback_devices, list) or not _is_error(fallback_devices):
                cloud, devices = fallback_cloud, fallback_devices
            else:
                raise TuyaCloudError(
                    "Tuya rechazó la consulta con ID virtual "
                    f"({first_error}) y también sin ID ({_error_detail(fallback_devices)})."
                )
        if isinstance(devices, list):
            result = devices
        elif isinstance(devices, dict):
            # Detectar error de autenticación / permisos de la API Tuya
            if _is_error(devices):
                detail = _error_detail(devices)
                _LOGGER.error(
                    "Tuya Cloud API error — %s. "
                    "Verifica: Access ID, Access Secret, región del proyecto "
                    "y que la cuenta de la app esté vinculada al proyecto IoT.",
                    detail,
                )
                raise TuyaCloudError(f"Tuya Cloud error: {detail}")
            result = devices.get("result")
            if not isinstance(result, list):
                _LOGGER.warning("Tuya Cloud returned unexpected payload: %s", devices)
                raise TuyaCloudError("Tuya Cloud respondió sin una lista de dispositivos")
        else:
            raise TuyaCloudError(
                f"Tuya Cloud no devolvió una respuesta válida ({type(devices).__name__})"
            )

        # Product functions label the otherwise product-specific DPS numbers.
        # A failed schema lookup is non-fatal: LAN control continues to work.
        for device in result:
            dev_id = device.get("id")
            if not dev_id:
                continue
            try:
                functions = cloud.getfunctions(dev_id)
                if isinstance(functions, dict):
                    functions = functions.get("result", functions.get("functions", []))
                if isinstance(functions, list):
                    device["_omni_tuya_functions"] = functions
            except Exception as err:
                _LOGGER.debug("Could not fetch Tuya functions for %s: %s", dev_id, err)
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
            "cloud_id": raw.get("id") or "",
            "uuid": raw.get("uuid") or raw.get("local_id") or "",
            "mac": raw.get("mac") or raw.get("mac_address") or "",
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
