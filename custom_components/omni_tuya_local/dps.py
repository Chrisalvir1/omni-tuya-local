"""Safe DPS discovery helpers.

Tuya DP numbers are product-specific.  This module exposes values observed on
the local LAN without guessing that an unknown writable DP is a safe control.
Cloud product functions are used only to improve the label when available.
"""

from __future__ import annotations

from typing import Any
import math

from .pet_feeder import function_id


# The following IDs are part of Tuya's documented ``sd`` robot-vacuum
# profile.  They are used only when the imported device identifies itself as
# that profile; every other product keeps the conservative ``DPS <id>`` label.
_ROBOT_VACUUM_DPS_LABELS = {
    "2": "Inicio de limpieza",
    "3": "Modo de limpieza",
    "4": "Control manual",
    "5": "Estado de limpieza",
    "6": "Batería",
    "7": "Vida del cepillo lateral",
    "8": "Vida del cepillo principal",
    "9": "Vida del filtro",
    "17": "Tiempo de limpieza",
    "18": "Fallo del robot",
}

_OUTLET_DPS_LABELS = {
    "1": "Toma 1",
    "2": "Toma 2",
    "3": "Toma 3",
    "4": "Toma 4",
    "5": "Toma 5",
    "6": "Toma 6",
    "7": "USB",
    "9": "Temporizador 1",
    "10": "Temporizador 2",
    "17": "Energía",
    "18": "Corriente",
    "19": "Potencia",
    "20": "Voltaje",
}

_ENERGY_DPS_LABELS = {
    "17": "Energía",
    "18": "Corriente",
    "19": "Potencia",
    "20": "Voltaje",
}

_SWITCH_DPS_LABELS = {
    "1": "Canal 1",
    "2": "Canal 2",
    "3": "Canal 3",
    "4": "Canal 4",
    "5": "Canal 5",
    "6": "Canal 6",
}


_LIGHT_DPS_LABELS = {
    "1": "Luz 1",
    "2": "Luz 2",
    "3": "Luz 3",
    "4": "Luz 4",
    "5": "Luz 5",
    "6": "Luz 6",
}

def dps_kind(value: Any) -> str | None:
    """Return the Home Assistant-safe kind for an observed DPS value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return "number"
    if isinstance(value, str) and len(value) <= 255:
        return "text"
    return None


def dps_label(config: dict[str, Any], dps_id: str | int) -> str:
    """Return a stable, human-friendly name without inventing semantics."""
    dps_id = str(dps_id)
    configured = (config.get("dps_map") or {}).get(dps_id)
    if isinstance(configured, dict) and configured.get("name"):
        return str(configured["name"])

    for function in config.get("tuya_functions") or []:
        if not isinstance(function, dict) or function_id(function) != dps_id:
            continue
        label = function.get("name") or function.get("code") or function.get("identifier")
        if label:
            return str(label).replace("_", " ").strip().title()

    dev_type = str(config.get("device_type") or "").lower()
    cat = str(config.get("category") or "").lower()
    domain = str(config.get("domain") or "").lower()
    product = str(config.get("product_name") or "").lower()

    if (
        dev_type == "robot_vacuum"
        or cat == "sd"
        or domain == "vacuum"
    ):
        standard_label = _ROBOT_VACUUM_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label

    if (
        dev_type in ("outlet", "power_strip")
        or cat in ("cz", "pc", "sp")
        or any(w in product for w in ("plug", "outlet", "socket", "tomacorriente", "enchufe", "power strip", "regleta", "duo"))
    ):
        standard_label = _OUTLET_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label

    if dev_type in ("light", "dimmer", "led_strip") or cat in ("dj", "dd", "fwd", "dc", "xktyd") or domain == "light":
        standard_label = _LIGHT_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label

    if dev_type == "switch" or cat in ("kg", "tgkg", "tgq", "dlq", "tdq") or domain == "switch":
        standard_label = _SWITCH_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label

    if dps_id in _ENERGY_DPS_LABELS and (
        dev_type in ("switch", "outlet", "power_strip")
        or cat in ("kg", "tgkg", "cz", "pc", "sp", "dlq", "tdq")
    ):
        return _ENERGY_DPS_LABELS[dps_id]

    return f"DPS {dps_id}"


def discovered_dps(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Return persisted LAN DPS schema, normalizing older stored data."""
    result: dict[str, dict[str, str]] = {}

    for dps_id, info in (config.get("discovered_dps") or {}).items():
        if not str(dps_id).isdigit() or not isinstance(info, dict):
            continue
        kind = info.get("kind")
        if kind not in {"boolean", "number", "text"}:
            continue
        result[str(dps_id)] = {
            "kind": kind,
            "name": str(info.get("name") or dps_label(config, dps_id)),
        }
    return result


def schema_from_dps(config: dict[str, Any], values: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Build the safe, persisted schema from an actual local status payload."""
    schema = discovered_dps(config)
    for dps_id, value in values.items():
        dps_id = str(dps_id)
        if not dps_id.isdigit():
            continue
        kind = dps_kind(value)
        if not kind:
            continue
        schema[dps_id] = {"kind": kind, "name": dps_label(config, dps_id)}
    return schema


def control_channels(config: dict[str, Any], raw_dps: dict[str, Any], platform: str) -> dict[str, str | None]:
    """Resolve product-specific control IDs before conventional 1..N channels.

    A channel number (switch_1) is not a DP ID (which may be 101). Unknown
    booleans remain read-only; merely discovering one never grants writes.
    """
    from .util import max_gangs_for_device

    channels: dict[str, str | None] = {}
    prefixes = ("switch", "power", "light", "led") if platform == "light" else ("switch", "power", "outlet")
    codes = set(prefixes)
    codes.update(f"{prefix}_{i}" for prefix in prefixes for i in range(1, 9))
    if platform == "light":
        codes.add("switch_led")
    for func in config.get("tuya_functions") or []:
        if not isinstance(func, dict):
            continue
        dp_id = function_id(func)
        code = str(func.get("code") or func.get("identifier") or "").lower()
        if dp_id and dp_id.isdigit() and code in codes and not func.get("read_only"):
            channels[dp_id] = dps_label(config, dp_id)

    for dp_id, desc in (config.get("dps_map") or {}).items():
        dp_id = str(dp_id)
        if not dp_id.isdigit():
            continue
        if isinstance(desc, dict):
            target = desc.get("platform")
            code = desc.get("code") or desc.get("semantic")
            if target and target != platform:
                continue
            if not target and code and code not in codes:
                continue
            if not target and any(key in desc for key in ("unit", "device_class", "scale", "options")):
                continue
            channels[dp_id] = desc.get("name")
        elif isinstance(desc, str) and desc not in {"brightness", "color_temp", "hsv", "mode"}:
            channels[dp_id] = desc

    if channels:
        return channels
    observed = discovered_dps(config)
    for i in range(1, max_gangs_for_device(config, raw_dps) + 1):
        dp_id = str(i)
        value = raw_dps.get(dp_id, raw_dps.get(i))
        info = observed.get(dp_id, {})
        if isinstance(value, bool) or info.get("kind") == "boolean":
            name = info.get("name")
            channels[dp_id] = name if name and name != f"DPS {dp_id}" else None
    # Common RGB firmware uses power DP 20. Do not manufacture DP 1 for it.
    if platform == "light" and not channels:
        if isinstance(raw_dps.get("20"), bool) or observed.get("20", {}).get("kind") == "boolean":
            channels["20"] = None
    return channels


def product_dps(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Describe authoritative product IDs without claiming LAN observations."""
    kinds = {"bool": "boolean", "boolean": "boolean", "integer": "number", "value": "number", "numeric": "number", "enum": "text", "string": "text"}
    result = {}
    for func in config.get("tuya_functions") or []:
        if not isinstance(func, dict):
            continue
        dp_id = function_id(func)
        kind = kinds.get(str(func.get("type") or "").lower())
        if dp_id and kind:
            result[dp_id] = {"kind": kind, "name": dps_label(config, dp_id)}
    return result


def query_dps_ids(config: dict[str, Any]) -> list[int]:
    """Request known product IDs, without probing arbitrary writable values."""
    ids = set(product_dps(config)) | set(discovered_dps(config))
    ids.update(str(key) for key in (config.get("dps_map") or {}) if str(key).isdigit())
    return sorted(int(key) for key in ids) or [1, 2, 9, 17, 18, 19, 20]

