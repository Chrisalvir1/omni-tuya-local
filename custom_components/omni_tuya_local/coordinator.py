from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    BACKOFF_POLL_INTERVAL,
    DEFAULT_DISCOVERY_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_FAILURES,
)
from .device import OmniTuyaDevice
from .dps import schema_from_dps
from .storage import TuyaDeviceStore

_LOGGER = logging.getLogger(__name__)

# Interval de poll reducido para alarm_kit — captura el trigger PIR efímero (DPS 106)
_ALARM_KIT_POLL_INTERVAL = 5  # segundos


class OmniTuyaLocalCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: TuyaDeviceStore) -> None:
        self.entry = entry
        self.store = store
        self.devices: dict[str, OmniTuyaDevice] = {}
        # Usamos set de ids para evitar callbacks duplicados (Bug #8)
        self._entity_refresh_callbacks: list[Any] = []
        self._registered_callback_ids: set[int] = set()
        self._udp_transports: list[Any] = []
        self._last_recovery_scan: float = 0.0
        self._recovery_scan_task: asyncio.Task | None = None
        self._lan_refresh_lock = asyncio.Lock()
        self._periodic_discovery_unsub = None
        self._verification_tasks: dict[str, asyncio.Task] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        await self._ensure_devices()
        device_items = list(self.devices.items())
        if not device_items:
            return {
                "devices": self.store.all(),
                "dps": {},
                "available": {},
            }

        # Ejecutar todas las consultas de estado en paralelo
        results = await asyncio.gather(
            *(device.async_status() for _, device in device_items),
            return_exceptions=True,
        )

        dps_by_device: dict[str, dict[str, Any]] = {}
        availability: dict[str, bool] = {}
        dps_schema_changed = False

        for (device_id, device), result in zip(device_items, results):
            if isinstance(result, Exception):
                _LOGGER.error("Error inesperado en polling para %s: %s", device_id, result)
                dps_by_device[device_id] = device.dps
            else:
                dps_by_device[device_id] = result

            # Persist only the shape observed on the LAN, not values.  This
            # lets entities remain visible after a restart even if a device is
            # temporarily offline, while avoiding unsafe guessed controls.
            config = self.store.get(device_id)
            detected_version = device.detected_protocol_version
            if (
                config
                and detected_version
                and str(config.get("version")) != detected_version
            ):
                updated = dict(config)
                updated["version"] = detected_version
                await self.store.add(updated)
                device.update_config(updated)
                config = updated
            if config and dps_by_device[device_id]:
                schema = schema_from_dps(config, dps_by_device[device_id])
                if schema != config.get("discovered_dps", {}):
                    updated = dict(config)
                    updated["discovered_dps"] = schema
                    await self.store.add(updated)
                    device.update_config(updated)
                    dps_schema_changed = True

            availability[device_id] = device.available
            # Backoff: si el device falla muchas veces, ajustar interval dinámicamente
            if device.consecutive_failures >= MAX_POLL_FAILURES:
                _LOGGER.debug(
                    "Device %s has %d consecutive failures — backing off",
                    device_id,
                    device.consecutive_failures,
                )

        # Ajustar update_interval dinámicamente según estado general de dispositivos
        self._adjust_poll_interval()
        self._schedule_lan_recovery_if_needed()

        if dps_schema_changed:
            self._notify_entity_refresh()

        return {
            "devices": self.store.all(),
            "dps": dps_by_device,
            "available": availability,
        }

    def _schedule_lan_recovery_if_needed(self) -> None:
        """Rescan LAN only after persistent failures, never every poll."""
        if not any(
            device.consecutive_failures >= MAX_POLL_FAILURES
            for device in self.devices.values()
        ):
            return
        now = time.monotonic()
        if (
            self._recovery_scan_task is not None
            and not self._recovery_scan_task.done()
        ) or now - self._last_recovery_scan < BACKOFF_POLL_INTERVAL:
            return
        self._last_recovery_scan = now
        self._recovery_scan_task = self.hass.async_create_task(
            self._async_recover_lan_addresses()
        )

    async def _async_recover_lan_addresses(self, proactive: bool = False) -> None:
        """Use Tuya broadcasts/scanning to repair a changed DHCP address."""
        from .discovery import async_scan_network

        async with self._lan_refresh_lock:
            _LOGGER.info(
                "%s Tuya LAN addresses by device ID/MAC",
                "Refreshing" if proactive else "Recovering persistent-failure",
            )
            try:
                # Each config entry uses a scoped store, but LAN discovery is
                # global. Use the singleton inventory so a DHCP change for
                # any Tuya MAC can be repaired by the single periodic scan.
                inventory = TuyaDeviceStore(self.hass)
                await inventory.async_load()
                found = await async_scan_network(
                    self.hass,
                    list(inventory.all().values()),
                    full_subnet_scan=not proactive,
                )
                changed = 0
                for config in found:
                    if config.get("synced") and config.get("device_id"):
                        previous = inventory.get(config["device_id"])
                        if previous and (
                            previous.get("host") != config.get("host")
                            or previous.get("ip") != config.get("ip")
                        ):
                            await inventory.add(config)
                            changed += 1
                if changed:
                    _LOGGER.info("Recovered %d Tuya LAN address(es) after rescan", changed)
                    for coordinator in self.hass.data.get(DOMAIN, {}).values():
                        if isinstance(coordinator, OmniTuyaLocalCoordinator):
                            await coordinator.async_reload_devices()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Automatic Tuya LAN recovery scan failed: %s", err)

    def _adjust_poll_interval(self) -> None:
        """Reducir frecuencia de poll si todos los dispositivos están unavailable.

        Si hay al menos un alarm_kit configurado y disponible, se usa un intervalo
        reducido (5 s) para capturar el trigger PIR efímero del sensor solar (DPS 106).
        """
        if not self.devices:
            return
        all_failed = all(
            d.consecutive_failures >= MAX_POLL_FAILURES
            for d in self.devices.values()
        )
        # Detectar si hay algún alarm_kit activo
        has_alarm_kit = any(
            cfg.get("device_type") == "alarm_kit" and cfg.get("enabled", True)
            for cfg in self.store.all().values()
        )
        if all_failed:
            target_seconds = BACKOFF_POLL_INTERVAL
        elif has_alarm_kit:
            target_seconds = _ALARM_KIT_POLL_INTERVAL
        else:
            target_seconds = DEFAULT_POLL_INTERVAL
        desired = timedelta(seconds=target_seconds)
        if self.update_interval != desired:
            self.update_interval = desired
            _LOGGER.debug(
                "Poll interval adjusted to %ss (all_failed=%s, has_alarm_kit=%s)",
                target_seconds, all_failed, has_alarm_kit,
            )

    async def _ensure_devices(self) -> None:
        """Sincronizar el dict de devices con la store."""
        configured = self.store.all()
        for device_id, config in configured.items():
            if not config.get("enabled", True):
                self.devices.pop(device_id, None)
                continue
            if device_id not in self.devices:
                self.devices[device_id] = OmniTuyaDevice(
                    self.hass, config, on_push=self._handle_push_update
                )
            else:
                # Actualizar config si cambió (p.ej. nueva IP)
                self.devices[device_id].update_config(config)
        # Eliminar devices ya no configurados
        for device_id in list(self.devices):
            if device_id not in configured or not configured[device_id].get("enabled", True):
                self.devices.pop(device_id, None)

    async def async_add_device(self, config: dict[str, Any]) -> dict[str, Any]:
        stored = await self.store.add(config)
        dev_id = stored["device_id"]
        if dev_id in self.devices:
            self.devices[dev_id].update_config(stored)
        else:
            self.devices[dev_id] = OmniTuyaDevice(
                self.hass, stored, on_push=self._handle_push_update
            )
        await self.async_request_refresh()
        self._notify_entity_refresh()
        return stored

    async def async_add_devices(self, configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stored = await self.store.add_many(configs)
        for config in stored:
            dev_id = config["device_id"]
            if dev_id in self.devices:
                self.devices[dev_id].update_config(config)
            else:
                self.devices[dev_id] = OmniTuyaDevice(
                    self.hass, config, on_push=self._handle_push_update
                )
        await self.async_request_refresh()
        self._notify_entity_refresh()
        return stored

    async def async_remove_device(self, device_id: str) -> bool:
        self.devices.pop(device_id, None)
        removed = await self.store.remove(device_id)
        await self.async_request_refresh()
        self._notify_entity_refresh()
        return removed

    async def async_reload_devices(self) -> None:
        """Recargar todos los devices desde la store y refrescar entidades."""
        # Actualizar configs de devices existentes antes de limpiar
        await self.store.async_load()
        configured = self.store.all()
        from homeassistant.helpers import device_registry as dr
        device_registry = dr.async_get(self.hass)

        # Actualizar los existentes primero
        for dev_id, config in configured.items():
            if dev_id in self.devices:
                self.devices[dev_id].update_config(config)
            
            # Sincronizar el nombre con el Device Registry de HA
            new_name = config.get("name")
            if new_name:
                device = device_registry.async_get_device(identifiers={(DOMAIN, dev_id)})
                # Solo forzamos la actualización si el nombre original configurado (no el renombrado localmente por el usuario en HA) cambió
                if device and device.original_name != new_name:
                    device_registry.async_update_device(device.id, original_name=new_name)

        # Eliminar los que ya no existen
        for dev_id in list(self.devices):
            if dev_id not in configured:
                self.devices.pop(dev_id, None)
        # Agregar los nuevos
        for dev_id, config in configured.items():
            if dev_id not in self.devices and config.get("enabled", True):
                self.devices[dev_id] = OmniTuyaDevice(
                    self.hass, config, on_push=self._handle_push_update
                )
        await self.async_request_refresh()
        self._notify_entity_refresh()

    async def async_setup(self) -> None:
        """Configurar e iniciar tareas en segundo plano del coordinator."""
        from .discovery import async_start_udp_listener
        self._udp_transports = await async_start_udp_listener(
            self.hass,
            self._handle_discovered_device
        )
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        discovery_owner = domain_data.get("_lan_discovery_owner")
        if discovery_owner in (None, self.entry.entry_id) and self._periodic_discovery_unsub is None:
            domain_data["_lan_discovery_owner"] = self.entry.entry_id
            async def _periodic_lan_discovery(_now) -> None:
                await self._async_recover_lan_addresses(proactive=True)

            self._periodic_discovery_unsub = async_track_time_interval(
                self.hass,
                _periodic_lan_discovery,
                timedelta(seconds=DEFAULT_DISCOVERY_INTERVAL),
            )

    def _handle_discovered_device(self, device_id: str, ip: str, version: str) -> None:
        """Callback para manejar el descubrimiento de un dispositivo."""
        config = self.store.get(device_id)
        if config:
            current_ip = config.get("host") or config.get("ip") or ""
            current_version = config.get("version") or "3.3"
            
            needs_update = False
            updated = dict(config)
            
            if current_ip != ip:
                _LOGGER.info(
                    "Device %s dynamic IP changed: %s → %s. Updating automatically.",
                    device_id, current_ip, ip
                )
                updated["host"] = ip
                updated["ip"] = ip
                needs_update = True
                
            if version and str(version) != str(current_version):
                _LOGGER.info(
                    "Device %s protocol version changed: %s → %s. Updating automatically.",
                    device_id, current_version, version
                )
                updated["version"] = str(version)
                needs_update = True
                
            if needs_update:
                self.hass.async_create_task(self._async_update_device(updated))

    async def _async_update_device(self, config: dict[str, Any]) -> None:
        await self.store.add(config)
        await self.async_reload_devices()

    async def async_shutdown(self) -> None:
        if self._periodic_discovery_unsub is not None:
            self._periodic_discovery_unsub()
            self._periodic_discovery_unsub = None
            if self.hass.data.get(DOMAIN, {}).get("_lan_discovery_owner") == self.entry.entry_id:
                self.hass.data[DOMAIN].pop("_lan_discovery_owner", None)
        for transport in self._udp_transports:
            try:
                transport.close()
            except Exception:
                pass
        self._udp_transports.clear()
        for device in self.devices.values():
            try:
                device.close()
            except Exception:
                pass
        self.devices.clear()

    def register_entity_refresh_callback(self, cb) -> None:
        """Registrar callback para recarga de entidades. Evita duplicados (Bug #8)."""
        cb_id = id(cb)
        if cb_id not in self._registered_callback_ids:
            self._entity_refresh_callbacks.append(cb)
            self._registered_callback_ids.add(cb_id)

    def _notify_entity_refresh(self) -> None:
        for cb in list(self._entity_refresh_callbacks):
            self.hass.async_create_task(cb())

    @callback
    def _handle_push_update(self, device_id: str, dps: dict[str, Any]) -> None:
        """Callback ejecutado desde el event loop cuando el listener TCP recibe un push."""
        if not self.data:
            self.data = {"devices": self.store.all(), "dps": {}, "available": {}}
        
        if device_id not in self.data["dps"]:
            self.data["dps"][device_id] = {}
            
        import time
        t = time.time()
        dps_copy = dict(dps)
        dps_copy["_push_time"] = t
        for k in dps.keys():
            dps_copy[f"_push_time_{k}"] = t
        
        self.data["dps"][device_id].update(dps_copy)
        self.data["available"][device_id] = True
        
        _LOGGER.debug("Coordinator updated state for %s from push: %s", device_id, dps_copy)
        self.async_set_updated_data(self.data)

    def get_device_config(self, device_id: str) -> dict[str, Any] | None:
        return self.store.get(device_id)

    def dps_value(self, device_id: str, dps_id: str = "1") -> Any:
        return (self.data or {}).get("dps", {}).get(device_id, {}).get(str(dps_id))

    def is_available(self, device_id: str) -> bool:
        return bool((self.data or {}).get("available", {}).get(device_id))

    def _publish_optimistic_state(self, device_id: str, dps: dict[str, Any]) -> None:
        """Publish a local command immediately; polling confirms it later."""
        data = self.data or {"devices": self.store.all(), "dps": {}, "available": {}}
        data.setdefault("dps", {}).setdefault(device_id, {}).update(dps)
        data.setdefault("available", {})[device_id] = True
        self.async_set_updated_data(data)

    def _schedule_command_verification(self, device_id: str) -> None:
        """Verify after control without keeping the service call waiting."""
        active = self._verification_tasks.get(device_id)
        if active and not active.done():
            return

        async def _verify() -> None:
            await asyncio.sleep(2)
            try:
                await self.async_request_refresh()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Background command verification failed for %s: %s", device_id, err)

        self._verification_tasks[device_id] = self.hass.async_create_task(_verify())

    async def async_set_status(self, device_id: str, value: bool, dps_id: int = 1) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_status(value, dps_id)
        if ok:
            self._publish_optimistic_state(device_id, {str(dps_id): value})
            self._schedule_command_verification(device_id)
        return ok

    async def async_set_value(self, device_id: str, dps_id: int, value: Any) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_value(dps_id, value)
        if ok:
            self._publish_optimistic_state(device_id, {str(dps_id): value})
            self._schedule_command_verification(device_id)
        return ok

    async def async_set_values(self, device_id: str, dps_dict: dict[str, Any]) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_values(dps_dict)
        if ok:
            self._publish_optimistic_state(
                device_id, {str(dps_id): value for dps_id, value in dps_dict.items()}
            )
            self._schedule_command_verification(device_id)
        return ok

    async def async_set_manual_feed_portions(self, device_id: str, portions: int) -> None:
        """Persist the selected manual-feed amount without sending a command.

        The amount is a Home Assistant preference.  It must survive a restart,
        DHCP address changes, and rediscovery of the same Tuya hardware ID.
        """
        config = self.store.get(device_id)
        if not config:
            raise ValueError(f"Tuya device {device_id} is not registered")
        updated = dict(config)
        updated["manual_feed_portions"] = portions
        await self.store.add(updated)
        if device_id in self.devices:
            self.devices[device_id].update_config(updated)

    async def async_fetch_raw_dps(self, device_id: str) -> dict[str, Any]:
        """Obtener DPS en tiempo real para diagnóstico."""
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return {}
        return await device.async_fetch_raw_dps()

    async def async_test_device(self, device_id: str) -> dict[str, Any]:
        """Probar conectividad LAN de un dispositivo y retornar resultado."""
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            config = self.store.get(device_id)
            if not config:
                return {"success": False, "error": "device_not_found"}
            device = OmniTuyaDevice(self.hass, config)

        res = await device.async_fetch_raw_dps()
        if isinstance(res, dict) and "dps" in res:
            return {
                "success": True,
                "device_id": device_id,
                "host": device.config.host,
                "version": device.config.version,
                "dps": res["dps"],
            }
        return {
            "success": False,
            "device_id": device_id,
            "host": device.config.host,
            "version": device.config.version,
            "error": res.get("error") if isinstance(res, dict) else "no_response",
            "raw": res,
        }
