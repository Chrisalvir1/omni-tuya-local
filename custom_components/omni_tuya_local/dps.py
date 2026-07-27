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

    if (
        config.get("device_type") == "robot_vacuum"
        or str(config.get("category") or "").lower() == "sd"
        or config.get("domain") == "vacuum"
    ):
        standard_label = _ROBOT_VACUUM_DPS_LABELS.get(dps_id)
        if standard_label:
            return standard_label
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
        if kind:
            schema[dps_id] = {"kind": kind, "name": dps_label(config, dps_id)}
    return schema
