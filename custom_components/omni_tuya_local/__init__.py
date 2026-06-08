from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .cloud import async_fetch_cloud_devices
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_REGION,
    CONF_VERSION,
    BUILD_NUMBER,
    DEFAULT_REGION,
    DEFAULT_VERSION,
    DEVICE_TYPES,
    DOMAIN,
    EXPORT_DOMAINS,
    INTEGRATION_VERSION,
    PLATFORMS,
    SERVICE_ADD_DEVICE,
    SERVICE_RELOAD_DEVICES,
    SERVICE_REMOVE_DEVICE,
    SERVICE_SCAN_NETWORK,
    SERVICE_SET_DEVICE_DOMAIN,
    SERVICE_SET_DEVICE_TYPE,
    SERVICE_SET_DEVICE_IP,
    SERVICE_SYNC_CLOUD,
    SERVICE_DIAGNOSTICS,
    SERVICE_TEST_DEVICE,
    SERVICE_FETCH_DPS,
)
from .coordinator import OmniTuyaLocalCoordinator
from .discovery import async_scan_network
from .storage import TuyaDeviceStore

_LOGGER = logging.getLogger(__name__)

ADD_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required("name"): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Optional(CONF_HOST, default=""): cv.string,
        vol.Optional(CONF_VERSION, default=DEFAULT_VERSION): cv.string,
        vol.Optional("domain", default="switch"): vol.In(EXPORT_DOMAINS),
        vol.Optional(CONF_DEVICE_TYPE, default="generic"): vol.In(list(DEVICE_TYPES)),
        vol.Optional("product_name", default=""): cv.string,
        vol.Optional("dps_map", default={}): dict,
    }
)

REMOVE_DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): cv.string})

SET_DEVICE_IP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_HOST): cv.string,
    }
)

SET_DEVICE_DOMAIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required("domain"): vol.In(EXPORT_DOMAINS),
    }
)

SET_DEVICE_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DEVICE_TYPE): vol.In(list(DEVICE_TYPES)),
    }
)

SYNC_CLOUD_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_KEY, default=""): cv.string,
        vol.Optional(CONF_API_SECRET, default=""): cv.string,
        vol.Optional(CONF_REGION, default=DEFAULT_REGION): cv.string,
        vol.Optional(CONF_DEVICE_ID, default=""): cv.string,
    }
)

TEST_DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): cv.string})
FETCH_DPS_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = TuyaDeviceStore(hass)
    await store.async_load()
    active_store = store

    if entry.data and entry.data.get(CONF_DEVICE_ID) and entry.data.get(CONF_LOCAL_KEY):
        await store.add(dict(entry.data))
        active_store = _ScopedTuyaDeviceStore(store, entry.data[CONF_DEVICE_ID])
    elif entry.data:
        store.cloud_config.update({k: v for k, v in entry.data.items() if v})
        await store.async_save()

    if (
        store.cloud_config.get(CONF_API_KEY)
        and store.cloud_config.get(CONF_API_SECRET)
        and not store.all()
    ):
        try:
            devices = await async_fetch_cloud_devices(
                hass,
                store.cloud_config[CONF_API_KEY],
                store.cloud_config[CONF_API_SECRET],
                store.cloud_config.get(CONF_REGION, DEFAULT_REGION),
                store.cloud_config.get(CONF_DEVICE_ID, ""),
            )
            await store.add_many(devices)
            _LOGGER.info("Imported %s Tuya devices during setup", len(devices))
        except Exception as err:
            _LOGGER.warning("Tuya cloud sync during setup failed: %s", err)

    coordinator = OmniTuyaLocalCoordinator(hass, entry, active_store)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass, entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok


def _coordinator(hass: HomeAssistant, entry_id: str) -> OmniTuyaLocalCoordinator:
    return hass.data[DOMAIN][entry_id]


class _ScopedTuyaDeviceStore:
    """Expone un único dispositivo almacenado a una config entry por dispositivo."""

    def __init__(self, store: TuyaDeviceStore, device_id: str) -> None:
        self._store = store
        self._device_id = device_id
        self.cloud_config = store.cloud_config

    async def async_load(self) -> None:
        await self._store.async_load()
        self.cloud_config = self._store.cloud_config

    async def async_save(self) -> None:
        await self._store.async_save()

    def all(self) -> dict[str, dict]:
        device = self._store.get(self._device_id)
        return {self._device_id: device} if device else {}

    def get(self, device_id: str) -> dict | None:
        if device_id != self._device_id:
            return None
        return self._store.get(device_id)

    async def add(self, config: dict) -> dict:
        return await self._store.add(config)

    async def add_many(self, configs: list[dict]) -> list[dict]:
        matching = [c for c in configs if c.get(CONF_DEVICE_ID) == self._device_id]
        return await self._store.add_many(matching)

    async def remove(self, device_id: str) -> bool:
        if device_id != self._device_id:
            return False
        return await self._store.remove(device_id)


def _async_register_services(hass: HomeAssistant, entry_id: str) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ADD_DEVICE):
        return

    async def add_device(call: ServiceCall) -> None:
        coord = _coordinator(hass, entry_id)
        await coord.async_add_device(dict(call.data))

    async def remove_device(call: ServiceCall) -> None:
        coord = _coordinator(hass, entry_id)
        await coord.async_remove_device(call.data[CONF_DEVICE_ID])

    async def set_device_ip(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        device_id = call.data[CONF_DEVICE_ID]
        host = call.data[CONF_HOST].strip()
        current = coord.store.get(device_id)
        if not current:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(current)
        updated[CONF_HOST] = host
        updated["ip"] = host
        stored = await coord.store.add(updated)
        await coord.async_reload_devices()
        return {"device": stored}

    async def set_device_domain(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        device_id = call.data[CONF_DEVICE_ID]
        current = coord.store.get(device_id)
        if not current:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(current)
        updated["domain"] = call.data["domain"]
        stored = await coord.store.add(updated)
        await coord.async_reload_devices()
        return {"device": stored}

    async def set_device_type(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        device_id = call.data[CONF_DEVICE_ID]
        current = coord.store.get(device_id)
        if not current:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(current)
        updated[CONF_DEVICE_TYPE] = call.data[CONF_DEVICE_TYPE]
        stored = await coord.store.add(updated)
        await coord.async_reload_devices()
        return {"device": stored}

    async def scan_network(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        found = await async_scan_network(hass, list(coord.store.all().values()))
        added = 0
        for device in found:
            if device.get("synced") and device.get(CONF_LOCAL_KEY):
                await coord.async_add_device(device)
                added += 1
        return {"found": len(found), "added": added, "devices": found}

    async def sync_cloud(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        cloud_config = dict(coord.store.cloud_config)
        cloud_config.update({k: v for k, v in call.data.items() if v})
        if not cloud_config.get(CONF_API_KEY) or not cloud_config.get(CONF_API_SECRET):
            raise ValueError("Tuya API key and API secret are required")
        coord.store.cloud_config.update(cloud_config)
        await coord.store.async_save()
        devices = await async_fetch_cloud_devices(
            hass,
            cloud_config[CONF_API_KEY],
            cloud_config[CONF_API_SECRET],
            cloud_config.get(CONF_REGION, DEFAULT_REGION),
            cloud_config.get(CONF_DEVICE_ID, ""),
        )
        imported = await coord.async_add_devices(devices)
        return {"imported": len(imported), "devices": imported}

    async def reload_devices(call: ServiceCall) -> None:
        coord = _coordinator(hass, entry_id)
        await coord.async_reload_devices()

    async def diagnostics(call: ServiceCall) -> dict[str, Any]:
        coord = _coordinator(hass, entry_id)
        all_devices = coord.store.all()
        devices_info = []
        for dev_id, config in all_devices.items():
            device = coord.devices.get(dev_id)
            devices_info.append({
                "device_id": dev_id,
                "name": config.get("name"),
                "host": config.get("host") or config.get("ip") or "",
                "version": config.get("version"),
                "domain": config.get("domain"),
                "device_type": config.get("device_type"),
                "product_name": config.get("product_name"),
                "available": coord.is_available(dev_id),
                "consecutive_failures": device.consecutive_failures if device else 0,
                "last_dps": coord.dps_value(dev_id) if coord.data else None,
                "dps_count": len((coord.data or {}).get("dps", {}).get(dev_id, {})),
            })
        return {
            "version": INTEGRATION_VERSION,
            "build": BUILD_NUMBER,
            "total_devices": len(all_devices),
            "available_devices": sum(1 for d in devices_info if d["available"]),
            "devices": devices_info,
        }

    async def test_device(call: ServiceCall) -> dict[str, Any]:
        """Probar conectividad LAN de un dispositivo específico."""
        coord = _coordinator(hass, entry_id)
        device_id = call.data[CONF_DEVICE_ID]
        result = await coord.async_test_device(device_id)
        return result

    async def fetch_dps(call: ServiceCall) -> dict[str, Any]:
        """Obtener todos los DPS de un dispositivo en tiempo real."""
        coord = _coordinator(hass, entry_id)
        device_id = call.data[CONF_DEVICE_ID]
        config = coord.store.get(device_id)
        if not config:
            raise ValueError(f"Device {device_id} not found")
        dps = await coord.async_fetch_raw_dps(device_id)
        return {
            "device_id": device_id,
            "name": config.get("name"),
            "host": config.get("host") or config.get("ip") or "",
            "version": config.get("version"),
            "dps": dps,
        }

    hass.services.async_register(DOMAIN, SERVICE_ADD_DEVICE, add_device, schema=ADD_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_DEVICE, remove_device, schema=REMOVE_DEVICE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DEVICE_IP, set_device_ip,
        schema=SET_DEVICE_IP_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DEVICE_DOMAIN, set_device_domain,
        schema=SET_DEVICE_DOMAIN_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DEVICE_TYPE, set_device_type,
        schema=SET_DEVICE_TYPE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SCAN_NETWORK, scan_network,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_CLOUD, sync_cloud,
        schema=SYNC_CLOUD_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_RELOAD_DEVICES, reload_devices)
    hass.services.async_register(
        DOMAIN, SERVICE_DIAGNOSTICS, diagnostics,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TEST_DEVICE, test_device,
        schema=TEST_DEVICE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_FETCH_DPS, fetch_dps,
        schema=FETCH_DPS_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
