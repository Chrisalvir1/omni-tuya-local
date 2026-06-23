from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BACKOFF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_FAILURES,
)
from .device import OmniTuyaDevice
from .storage import TuyaDeviceStore

_LOGGER = logging.getLogger(__name__)


class OmniTuyaLocalCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: TuyaDeviceStore) -> None:
        self.entry = entry
        self.store = store
        self.devices: dict[str, OmniTuyaDevice] = {}
        # Usamos set de ids para evitar callbacks duplicados (Bug #8)
        self._entity_refresh_callbacks: list[Any] = []
        self._registered_callback_ids: set[int] = set()
        self._udp_transports: list[Any] = []
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

        for (device_id, device), result in zip(device_items, results):
            if isinstance(result, Exception):
                _LOGGER.error("Error inesperado en polling para %s: %s", device_id, result)
                dps_by_device[device_id] = device.dps
            else:
                dps_by_device[device_id] = result

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

        return {
            "devices": self.store.all(),
            "dps": dps_by_device,
            "available": availability,
        }

    def _adjust_poll_interval(self) -> None:
        """Reducir frecuencia de poll si todos los dispositivos están unavailable."""
        if not self.devices:
            return
        all_failed = all(
            d.consecutive_failures >= MAX_POLL_FAILURES
            for d in self.devices.values()
        )
        target_seconds = BACKOFF_POLL_INTERVAL if all_failed else DEFAULT_POLL_INTERVAL
        desired = timedelta(seconds=target_seconds)
        if self.update_interval != desired:
            self.update_interval = desired
            _LOGGER.debug(
                "Poll interval adjusted to %ss (all_failed=%s)",
                target_seconds, all_failed,
            )

    async def _ensure_devices(self) -> None:
        """Sincronizar el dict de devices con la store."""
        configured = self.store.all()
        for device_id, config in configured.items():
            if not config.get("enabled", True):
                self.devices.pop(device_id, None)
                continue
            if device_id not in self.devices:
                self.devices[device_id] = OmniTuyaDevice(self.hass, config)
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
            self.devices[dev_id] = OmniTuyaDevice(self.hass, stored)
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
                self.devices[dev_id] = OmniTuyaDevice(self.hass, config)
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
        # Actualizar los existentes primero
        for dev_id, config in configured.items():
            if dev_id in self.devices:
                self.devices[dev_id].update_config(config)
        # Eliminar los que ya no existen
        for dev_id in list(self.devices):
            if dev_id not in configured:
                self.devices.pop(dev_id, None)
        # Agregar los nuevos
        for dev_id, config in configured.items():
            if dev_id not in self.devices and config.get("enabled", True):
                self.devices[dev_id] = OmniTuyaDevice(self.hass, config)
        await self.async_request_refresh()
        self._notify_entity_refresh()

    async def async_setup(self) -> None:
        """Configurar e iniciar tareas en segundo plano del coordinator."""
        from .discovery import async_start_udp_listener
        self._udp_transports = await async_start_udp_listener(
            self.hass,
            self._handle_discovered_device
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

    def get_device_config(self, device_id: str) -> dict[str, Any] | None:
        return self.store.get(device_id)

    def dps_value(self, device_id: str, dps_id: str = "1") -> Any:
        return (self.data or {}).get("dps", {}).get(device_id, {}).get(str(dps_id))

    def is_available(self, device_id: str) -> bool:
        return bool((self.data or {}).get("available", {}).get(device_id))

    async def async_set_status(self, device_id: str, value: bool, dps_id: int = 1) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_status(value, dps_id)
        await asyncio.sleep(0)
        await self.async_request_refresh()
        return ok

    async def async_set_value(self, device_id: str, dps_id: int, value: Any) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_value(dps_id, value)
        await asyncio.sleep(0)
        await self.async_request_refresh()
        return ok

    async def async_set_values(self, device_id: str, dps_dict: dict[str, Any]) -> bool:
        await self._ensure_devices()
        device = self.devices.get(device_id)
        if not device:
            return False
        ok = await device.async_set_values(dps_dict)
        await asyncio.sleep(0)
        await self.async_request_refresh()
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
