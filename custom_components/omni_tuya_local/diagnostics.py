"""Diagnostics support for Omni Tuya Local."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator

TO_REDACT = {
    "local_key",
    "api_key",
    "api_secret",
    "access_id",
    "access_secret",
    "cloud_secret",
    "gateway_local_key",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]

    devices_data = {}
    for dev_id, config in coordinator.store.all().items():
        dev_inst = coordinator.devices.get(dev_id)
        devices_data[dev_id] = {
            "config": config,
            "available": coordinator.is_available(dev_id),
            "protocol_version": dev_inst.detected_protocol_version if dev_inst else config.get("version"),
            "raw_dps": dev_inst.dps if dev_inst else {},
            "consecutive_failures": dev_inst.consecutive_failures if dev_inst else 0,
            "last_error": dev_inst.last_error_detail if dev_inst else "",
        }

    return async_redact_data(
        {
            "entry_data": dict(entry.data),
            "entry_options": dict(entry.options),
            "device_count": len(coordinator.store.all()),
            "devices": devices_data,
        },
        TO_REDACT,
    )


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a specific device."""
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]

    dev_id = None
    for domain, ident in device.identifiers:
        if domain == DOMAIN:
            dev_id = ident
            break

    config = coordinator.get_device_config(dev_id) if dev_id else None
    dev_inst = coordinator.devices.get(dev_id) if dev_id else None

    return async_redact_data(
        {
            "device_id": dev_id,
            "device_name": device.name,
            "model": device.model,
            "sw_version": device.sw_version,
            "config": config,
            "available": coordinator.is_available(dev_id) if dev_id else False,
            "detected_protocol": dev_inst.detected_protocol_version if dev_inst else (config.get("version") if config else None),
            "raw_dps": dev_inst.dps if dev_inst else {},
            "consecutive_failures": dev_inst.consecutive_failures if dev_inst else 0,
            "last_error": dev_inst.last_error_detail if dev_inst else "",
        },
        TO_REDACT,
    )
