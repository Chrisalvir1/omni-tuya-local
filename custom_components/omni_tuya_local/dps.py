"""Safe DPS discovery helpers.

Tuya DP numbers are product-specific.  This module exposes values observed on
the local LAN without guessing that an unknown writable DP is a safe control.
Cloud product functions are used only to improve the label when available.
"""

from __future__ import annotations

from typing import Any

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

_DOOR_SENSOR_DPS_LABELS = {
    "1": "Puerta",
    "2": "Batería",
    "3": "Estado de batería",
    "4": "Antisabotaje",
}



def dps_kind(value: Any) -> str | None:
    """Return the Home Assistant-safe kind for an observed DPS value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
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

    if (
        dev_type in ("door_sensor", "window_sensor")
        or cat in ("mcs", "cs")
        or any(w in product for w in ("puerta", "door", "门磁", "contact", "contacto", "apertura", "magnetic", "ventana", "window", "窗"))
    ):
        if dps_id == "1" and (dev_type == "window_sensor" or cat == "cs" or any(w in product for w in ("ventana", "window", "窗"))):
            return "Ventana"
        standard_label = _DOOR_SENSOR_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label

    if dps_id in _ENERGY_DPS_LABELS:
        return _ENERGY_DPS_LABELS[dps_id]

    return f"DPS {dps_id}"


def discovered_dps(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Return persisted LAN DPS schema, normalizing older stored data."""
    from .util import max_gangs_for_device

    result: dict[str, dict[str, str]] = {}
    max_gangs = max_gangs_for_device(config)
    dev_type = str(config.get("device_type") or "").lower()
    cat = str(config.get("category") or "").lower()
    is_switch_or_light = (
        config.get("domain") in ("switch", "light")
        or dev_type in ("switch", "outlet", "power_strip", "light")
        or cat in ("kg", "tgkg", "tgq")
    )
    _internal_control_dps = {
        "7", "8", "9", "10", "11", "12", "14", "15", "16",
        "21", "22", "23", "24", "25", "26", "38", "39", "40",
    }

    for dps_id, info in (config.get("discovered_dps") or {}).items():
        if not str(dps_id).isdigit() or not isinstance(info, dict):
            continue
        kind = info.get("kind")
        if kind not in {"boolean", "number", "text"}:
            continue
        if is_switch_or_light:
            if kind == "boolean" and int(dps_id) > max_gangs:
                continue
            if str(dps_id) in _internal_control_dps:
                continue
        result[str(dps_id)] = {
            "kind": kind,
            "name": str(info.get("name") or dps_label(config, dps_id)),
        }
    return result


def schema_from_dps(config: dict[str, Any], values: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Build the safe, persisted schema from an actual local status payload."""
    from .util import max_gangs_for_device

    max_gangs = max_gangs_for_device(config)
    dev_type = str(config.get("device_type") or "").lower()
    cat = str(config.get("category") or "").lower()
    is_switch_or_light = (
        config.get("domain") in ("switch", "light")
        or dev_type in ("switch", "outlet", "power_strip", "light")
        or cat in ("kg", "tgkg", "tgq")
    )
    _internal_control_dps = {
        "7", "8", "9", "10", "11", "12", "14", "15", "16",
        "21", "22", "23", "24", "25", "26", "38", "39", "40",
    }

    schema = discovered_dps(config)
    for dps_id, value in values.items():
        dps_id = str(dps_id)
        if not dps_id.isdigit():
            continue
        kind = dps_kind(value)
        if not kind:
            continue
        if is_switch_or_light:
            if kind == "boolean" and int(dps_id) > max_gangs:
                continue
            if dps_id in _internal_control_dps:
                continue
        schema[dps_id] = {"kind": kind, "name": dps_label(config, dps_id)}
    return schema

