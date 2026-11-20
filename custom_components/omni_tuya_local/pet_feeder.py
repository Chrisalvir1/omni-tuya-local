"""Helpers for Tuya pet feeders.

Pet feeders are not a uniform Tuya category.  In particular, video feeders use
an IPC-specific, write-only *feed_publish* value DP, while older feeders often
use *manual_feed* or *quick_feed*.  Keep that knowledge in one place and use
the product's function schema whenever it is available.
"""

from __future__ import annotations

from typing import Any


_VALUE_FEED_CODES = {"feed_publish", "manual_feed"}
_BOOLEAN_FEED_CODES = {"quick_feed"}


def function_id(function: dict[str, Any]) -> str | None:
    """Return a DP id from the variations returned by Tuya Cloud."""
    value = function.get("dp_id", function.get("dpId", function.get("id")))
    return str(value) if value is not None and str(value).isdigit() else None


def pet_feeder_feed(config: dict[str, Any], raw_dps: dict[str, Any]) -> tuple[str, str] | None:
    """Return (DP id, kind) for a manual feed command.

    ``kind`` is ``value`` for a serving count or ``bool`` for the legacy quick
    feed command.  A user/imported schema always wins over historical DP-id
    fallbacks.
    """
    configured = config.get("pet_feeder_feed_dp")
    if configured:
        return str(configured), str(config.get("pet_feeder_feed_kind") or "value")

    for function in config.get("tuya_functions") or []:
        if not isinstance(function, dict):
            continue
        dp_id = function_id(function)
        code = str(function.get("code") or function.get("identifier") or "").lower()
        if dp_id and code in _VALUE_FEED_CODES:
            return dp_id, "value"
        if dp_id and code in _BOOLEAN_FEED_CODES:
            return dp_id, "bool"

    # The stored schema records observed types without persisting DPS
    # values. Use it to restore the same switch before the first LAN poll.
    discovered = config.get("discovered_dps") or {}
    for dp_id, kind, expected_type in (
        ("3", "value", "number"),
        ("201", "value", "number"),
        ("2", "bool", "boolean"),
    ):
        value = raw_dps.get(dp_id)
        if value is None:
            if (discovered.get(dp_id) or {}).get("kind") == expected_type:
                return dp_id, kind
        elif kind == "bool":
            if isinstance(value, bool):
                return dp_id, kind
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            return dp_id, kind
    return None


def pet_feeder_clean_hopper(config: dict[str, Any]) -> tuple[str, Any] | None:
    """Return an explicitly declared hopper-cleaning command, if any."""
    dp_id = config.get("pet_feeder_clean_hopper_dp")
    if not dp_id:
        return None
    return str(dp_id), config.get("pet_feeder_clean_hopper_value", True)
