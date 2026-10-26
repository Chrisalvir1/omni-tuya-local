from __future__ import annotations

import asyncio
import copy
import logging
from typing import Any

import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .cloud import async_allocate_camera_stream, async_fetch_cloud_devices
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
from .registry import device_for_entry

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
        vol.Optional(CONF_REGION): cv.string,
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
        # Config-entry data is the bootstrap snapshot from the day the device
        # was added.  Do not overwrite the durable inventory on every restart:
        # it contains cloud-renamed devices, rediscovered IPs, refreshed keys,
        # and user settings saved after that initial setup.
        if not store.get(entry.data[CONF_DEVICE_ID]):
            await store.add(dict(entry.data))
        active_store = _ScopedTuyaDeviceStore(store, entry.data[CONF_DEVICE_ID])
    elif entry.data:
        store.cloud_config.update({k: v for k, v in entry.data.items() if v})
        await store.async_save()

    coordinator = OmniTuyaLocalCoordinator(hass, entry, active_store)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _async_register_camera_stream_websocket(hass)
    async_migrate_primary_entity_ids(hass, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass, entry.entry_id)

    # The cloud-sync control is integration-wide, not a physical Tuya device.
    # Remove the virtual device created by older releases so it no longer
    # appears under every configured device after an update/restart.
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Remove old button entities that used per-entry unique_ids
    old_entity_id = entity_registry.async_get_entity_id("button", DOMAIN, f"{DOMAIN}_{entry.entry_id}_sync_cloud")
    if old_entity_id:
        entity_registry.async_remove(old_entity_id)

    try:
        hub_device = device_for_entry(device_registry, "hub", entry.entry_id)
        if hub_device:
            device_registry.async_remove_device(hub_device.id)
    except Exception as err:
        _LOGGER.debug("Legacy hub cleanup skipped: %s", err)

    # Limpiar entidades duplicadas/obsoletas de dispositivos (canales no físicos, sensores espurios, luces fantasma)
    try:
        await async_cleanup_device_entities(hass, coordinator)
    except Exception as err:
        _LOGGER.error("Error during initial entity cleanup: %s", err, exc_info=True)

    async def _post_setup_cleanup() -> None:
        await asyncio.sleep(2)
        try:
            await async_cleanup_device_entities(hass, coordinator)
        except Exception as err:
            _LOGGER.debug("Error during deferred entity cleanup: %s", err)

    hass.async_create_task(_post_setup_cleanup())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        # Platform entities are unloaded with the entry.  Allow the singleton
        # cloud-sync button to be registered again when the integration is
        # subsequently reloaded.
        if not any(
            isinstance(value, OmniTuyaLocalCoordinator)
            for value in hass.data[DOMAIN].values()
        ):
            hass.data[DOMAIN].pop("_global_sync_button_added", None)
            hass.data[DOMAIN].pop("_cloud_sync_scheduled", None)
            cloud_sync_unsub = hass.data[DOMAIN].pop("_cloud_sync_unsub", None)
            if cloud_sync_unsub:
                cloud_sync_unsub()
    return unload_ok



async def _async_fresh_camera_url(hass: HomeAssistant, entity_id: str) -> str:
    """Return a newly allocated URL for an authenticated Omni camera request."""
    entity_entry = er.async_get(hass).async_get(entity_id)
    if (
        entity_entry is None
        or entity_entry.domain != "camera"
        or entity_entry.platform != DOMAIN
    ):
        raise ValueError("Omni Tuya camera not found")

    prefix = f"{DOMAIN}_"
    suffix = "_camera"
    unique_id = entity_entry.unique_id
    if not unique_id.startswith(prefix) or not unique_id.endswith(suffix):
        raise ValueError("Omni Tuya camera not found")
    device_id = unique_id[len(prefix) : -len(suffix)]

    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, OmniTuyaLocalCoordinator):
            continue
        config = coordinator.get_device_config(device_id)
        if not config:
            continue
        cloud_config = getattr(coordinator.store, "cloud_config", {}) or {}
        return await async_allocate_camera_stream(
            hass,
            cloud_config.get(CONF_API_KEY, ""),
            cloud_config.get(CONF_API_SECRET, ""),
            cloud_config.get(CONF_REGION, DEFAULT_REGION),
            config.get("cloud_id") or device_id,
        )
    raise ValueError("Omni Tuya camera not found")


def _async_register_camera_stream_websocket(hass: HomeAssistant) -> None:
    """Register an authenticated bridge endpoint for fresh Tuya URLs."""
    if hass.data.get(DOMAIN, {}).get("_camera_stream_websocket_registered"):
        return

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "omni_tuya_local/camera_stream",
            vol.Required("entity_id"): cv.entity_id,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def handle_camera_stream(hass: HomeAssistant, connection, msg):
        """Allocate a one-session RTSP URL without persisting or logging it."""
        try:
            url = await _async_fresh_camera_url(hass, msg["entity_id"])
        except ValueError as err:
            connection.send_error(msg["id"], "not_found", str(err))
            return
        except Exception:
            # Cloud/client errors may contain the signed URL; never echo them.
            connection.send_error(
                msg["id"], "unknown_error", "Could not allocate Tuya camera stream"
            )
            return
        connection.send_result(msg["id"], {"url": url})

    websocket_api.async_register_command(hass, handle_camera_stream)
    hass.data.setdefault(DOMAIN, {})["_camera_stream_websocket_registered"] = True


def _coordinator(hass: HomeAssistant, entry_id: str) -> OmniTuyaLocalCoordinator:
    return hass.data[DOMAIN][entry_id]


def _coordinator_for_device(
    hass: HomeAssistant, device_id: str, fallback_entry_id: str
) -> OmniTuyaLocalCoordinator:
    """Find the config-entry coordinator that owns a device-scoped action.

    Integration services are registered only once, by whichever config entry
    starts first.  Each entry has a scoped view of the shared inventory, so
    using that first coordinator for every service made diagnostics fail with
    an unhelpful ``Unknown error`` for every other device.
    """
    for coordinator in _coordinators(hass):
        if coordinator.store.get(device_id):
            return coordinator
    return _coordinator(hass, fallback_entry_id)


def _coordinators(hass: HomeAssistant) -> list[OmniTuyaLocalCoordinator]:
    """Return only config-entry coordinators, excluding integration state."""
    return [
        value for value in hass.data.get(DOMAIN, {}).values()
        if isinstance(value, OmniTuyaLocalCoordinator)
    ]


async def async_reload_linked_entries(hass: HomeAssistant, device_ids: set[str]) -> None:
    """Rebuild existing entities after a product-schema refresh, retaining IDs.

    Merely refreshing the coordinator adds new entities but leaves the old
    entity objects' labels, units and capabilities bound to the old schema.
    Reload through HA so HomeKit receives fresh entity metadata too.
    """
    entries = [entry for entry in list(hass.config_entries.async_entries(DOMAIN)) if entry.data.get(CONF_DEVICE_ID) in device_ids or not entry.data.get(CONF_DEVICE_ID)]
    semaphore = asyncio.Semaphore(4)

    async def reload(entry):
        async with semaphore:
            return await hass.config_entries.async_reload(entry.entry_id)

    results = await asyncio.gather(*(reload(entry) for entry in entries), return_exceptions=True)
    failed = [entry.entry_id for entry, result in zip(entries, results) if isinstance(result, Exception) or result is False]
    if failed:
        raise HomeAssistantError(f"Tuya metadata saved, but {len(failed)} config entries could not reload")


def async_migrate_primary_entity_ids(hass: HomeAssistant, coordinator: OmniTuyaLocalCoordinator) -> None:
    """Correct a control's DP identity while retaining HA's entity_id.

    HomeKit derives accessory identity from entity_id. Migrate only an
    unambiguous single-channel product and never overwrite another entity.
    """
    from .dps import control_channels

    registry = er.async_get(hass)
    for device_id, config in coordinator.store.all().items():
        domain = config.get("domain")
        if domain not in {"switch", "light"}:
            continue
        raw = (coordinator.data or {}).get("dps", {}).get(device_id, {})
        channels = control_channels(config, raw, domain)
        if len(channels) != 1:
            continue
        dp_id = next(iter(channels))
        if dp_id == "1":
            continue
        old_uid = f"{DOMAIN}_{device_id}"
        new_uid = f"{old_uid}_{dp_id}"
        old_id = registry.async_get_entity_id(domain, DOMAIN, old_uid)
        if not old_id or registry.async_get_entity_id(domain, DOMAIN, new_uid):
            continue
        entity = registry.async_get(old_id)
        if entity and entity.config_entry_id == coordinator.entry.entry_id:
            registry.async_update_entity(old_id, new_unique_id=new_uid)


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


async def async_cleanup_device_entities(
    hass: HomeAssistant, coordinator: OmniTuyaLocalCoordinator
) -> None:
    """Remove only this entry's primary entities after an explicit domain change.

    Device names, channel-count guesses and DP numbers cannot prove that a
    sensor is obsolete. Never delete telemetry, helpers or another entry's
    entities during discovery or a temporary device outage.
    """
    entity_registry = er.async_get(hass)
    for dev_id, config in coordinator.store.all().items():
        domain = config.get("domain")
        if domain not in {"switch", "light"}:
            continue
        old_domain = "light" if domain == "switch" else "switch"
        prefix = f"{DOMAIN}_{dev_id}"
        for ent in list(entity_registry.entities.values()):
            if (
                ent.platform != DOMAIN
                or ent.config_entry_id != coordinator.entry.entry_id
                or ent.domain != old_domain
            ):
                continue
            uid = ent.unique_id or ""
            suffix = uid[len(prefix):] if uid.startswith(prefix) else None
            if suffix == "" or (suffix and suffix.startswith("_") and suffix[1:].isdigit()):
                entity_registry.async_remove(ent.entity_id)



def _async_register_services(hass: HomeAssistant, entry_id: str) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ADD_DEVICE):
        return

    async def add_device(call: ServiceCall) -> None:
        coord = _coordinator(hass, entry_id)
        await coord.async_add_device(dict(call.data))

    async def remove_device(call: ServiceCall) -> None:
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
        await coord.async_remove_device(device_id)

    async def set_device_ip(call: ServiceCall) -> dict[str, Any]:
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
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
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
        current = coord.store.get(device_id)
        if not current:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(current)
        updated["domain"] = call.data["domain"]
        stored = await coord.store.add(updated)
        await async_cleanup_device_entities(hass, coord)
        await coord.async_reload_devices()
        return {"device": stored}

    async def set_device_type(call: ServiceCall) -> dict[str, Any]:
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
        current = coord.store.get(device_id)
        if not current:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(current)
        updated[CONF_DEVICE_TYPE] = call.data[CONF_DEVICE_TYPE]
        stored = await coord.store.add(updated)
        await async_cleanup_device_entities(hass, coord)
        await coord.async_reload_devices()
        return {"device": stored}

    async def scan_network(call: ServiceCall) -> dict[str, Any]:
        store = TuyaDeviceStore(hass)
        await store.async_load()
        found = await async_scan_network(hass, list(store.all().values()))
        added = 0
        for device in found:
            if device.get("synced") and device.get(CONF_LOCAL_KEY):
                await store.add(device)
                added += 1

        if added > 0:
            for coord in _coordinators(hass):
                await coord.async_reload_devices()

        return {"found": len(found), "updated": added, "devices": found}

    async def sync_cloud(call: ServiceCall) -> dict[str, Any]:
        store = TuyaDeviceStore(hass)
        await store.async_load()
        cloud_config = dict(store.cloud_config)
        cloud_config.update({k: v for k, v in call.data.items() if v})
        if not cloud_config.get(CONF_API_KEY) or not cloud_config.get(CONF_API_SECRET):
            raise HomeAssistantError("Tuya API key and API secret are required")
        store.cloud_config.update(cloud_config)
        await store.async_save()
        devices = await async_fetch_cloud_devices(
            hass,
            cloud_config[CONF_API_KEY],
            cloud_config[CONF_API_SECRET],
            cloud_config.get(CONF_REGION, DEFAULT_REGION),
            cloud_config.get(CONF_DEVICE_ID, ""),
        )
        before_sync = copy.deepcopy(store.all())
        imported = await store.add_many(devices)

        new_inventory_ids = [
            device[CONF_DEVICE_ID] for device in imported
            if device[CONF_DEVICE_ID] not in before_sync
        ]
        updated_inventory_ids = [
            device[CONF_DEVICE_ID] for device in imported
            if device[CONF_DEVICE_ID] in before_sync
            and device != before_sync[device[CONF_DEVICE_ID]]
        ]

        # Smart Life names are cloud metadata.  Keep the config-entry title in
        # sync too; otherwise the device card continues showing the old name
        # even though the inventory was refreshed successfully.
        entries_by_device_id = {
            config_entry.data.get(CONF_DEVICE_ID): config_entry
            for config_entry in hass.config_entries.async_entries(DOMAIN)
        }
        for device in imported:
            config_entry = entries_by_device_id.get(device[CONF_DEVICE_ID])
            name = device.get("name")
            if config_entry and name and config_entry.title != name:
                hass.config_entries.async_update_entry(config_entry, title=name)

        # Crear entrada para cada dispositivo nuevo
        existing_entries = set(entries_by_device_id)
        new_entry_devices: list[dict[str, Any]] = []
        for dev in imported:
            if dev["device_id"] not in existing_entries:
                new_entry_devices.append(dev)
                hass.async_create_task(
                    hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "import"},
                        data=dev,
                    )
                )

        await async_reload_linked_entries(hass, {device[CONF_DEVICE_ID] for device in imported})

        return {
            "found": len(devices),
            "new": len(new_entry_devices),
            "updated": len(updated_inventory_ids),
            "unchanged": len(imported) - len(new_inventory_ids) - len(updated_inventory_ids),
            "new_devices": [
                {"device_id": device[CONF_DEVICE_ID], "name": device.get("name") or device[CONF_DEVICE_ID]}
                for device in new_entry_devices
            ],
            "updated_devices": [
                {"device_id": device_id, "name": (store.get(device_id) or {}).get("name") or device_id}
                for device_id in updated_inventory_ids
            ],
        }

    # Cloud inventory sync is exposed as a user-invoked service only.
    # Commands, polling and DPS reads use the local device transport.
    async def reload_devices(call: ServiceCall) -> None:
        coord = _coordinator(hass, entry_id)
        await coord.async_reload_devices()

    async def diagnostics(call: ServiceCall) -> dict[str, Any]:
        # Services are registered once per integration, but each config entry
        # may expose only its own device through a scoped store.
        device_owners: dict[str, OmniTuyaLocalCoordinator] = {}
        for coordinator in _coordinators(hass):
            for dev_id in coordinator.store.all():
                device_owners.setdefault(dev_id, coordinator)
        devices_info = []
        for dev_id, coordinator in device_owners.items():
            config = coordinator.store.get(dev_id) or {}
            device = coordinator.devices.get(dev_id)
            devices_info.append({
                "device_id": dev_id,
                "name": config.get("name"),
                "host": config.get("host") or config.get("ip") or "",
                "version": config.get("version"),
                "domain": config.get("domain"),
                "device_type": config.get("device_type"),
                "product_name": config.get("product_name"),
                "available": coordinator.is_available(dev_id),
                "consecutive_failures": device.consecutive_failures if device else 0,
                "last_error": device.last_error_detail if device else "",
                "last_dps": coordinator.dps_value(dev_id) if coordinator.data else None,
                "dps_count": len((coordinator.data or {}).get("dps", {}).get(dev_id, {})),
            })
        return {
            "version": INTEGRATION_VERSION,
            "build": BUILD_NUMBER,
            "total_devices": len(device_owners),
            "available_devices": sum(1 for d in devices_info if d["available"]),
            "devices": devices_info,
        }

    async def test_device(call: ServiceCall) -> dict[str, Any]:
        """Probar conectividad LAN de un dispositivo específico."""
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
        result = await coord.async_test_device(device_id)
        return result

    async def fetch_dps(call: ServiceCall) -> dict[str, Any]:
        """Obtener todos los DPS de un dispositivo en tiempo real."""
        device_id = call.data[CONF_DEVICE_ID]
        coord = _coordinator_for_device(hass, device_id, entry_id)
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
