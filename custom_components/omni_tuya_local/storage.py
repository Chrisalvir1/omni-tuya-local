from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import normalize_device

_LOGGER = logging.getLogger(__name__)


class TuyaDeviceStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._devices: dict[str, dict] = {}
        self.cloud_config: dict = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        raw_devices = data.get("devices") or {}
        loaded: dict[str, dict] = {}
        for dev_id, config in raw_devices.items():
            # Validar que el device_id no esté vacío (Bug #7)
            real_id = config.get("device_id") or dev_id
            if not real_id or not str(real_id).strip():
                _LOGGER.warning("Skipping stored device with empty device_id (key=%s)", dev_id)
                continue
            config.setdefault("device_id", real_id)
            try:
                normalized = normalize_device(config)
                loaded[normalized["device_id"]] = normalized
            except Exception as err:
                _LOGGER.warning("Could not load stored device %s: %s", dev_id, err)
        self._devices = loaded
        self.cloud_config = dict(data.get("cloud_config") or {})

    async def async_save(self) -> None:
        """Guardar usando escritura atómica para evitar corrupción."""
        await self._store.async_save({
            "devices": self._devices,
            "cloud_config": self.cloud_config,
        })

    def all(self) -> dict[str, dict]:
        return dict(self._devices)

    def get(self, device_id: str) -> dict | None:
        if not device_id:
            return None
        return self._devices.get(device_id)

    async def add(self, config: dict) -> dict:
        """Agregar o actualizar un dispositivo. Valida device_id antes de guardar."""
        normalized = normalize_device(config)
        dev_id = normalized.get("device_id", "")
        if not dev_id or not str(dev_id).strip():
            raise ValueError("Cannot add device with empty device_id")
        self._devices[dev_id] = normalized
        await self.async_save()
        return normalized

    async def add_many(self, configs: list[dict]) -> list[dict]:
        imported = []
        for config in configs:
            try:
                normalized = normalize_device(config)
                dev_id = normalized.get("device_id", "")
                if not dev_id or not str(dev_id).strip():
                    _LOGGER.warning("Skipping device with empty device_id during bulk import")
                    continue
                # Merge if exists
                if dev_id in self._devices:
                    existing = self._devices[dev_id]
                    # Cloud data may refresh the local key and product schema,
                    # but it must never discard local IP/discovery state or the
                    # user's persisted serving preference.
                    for key in (
                        "name", "local_key", "version", "product_name", "product_id",
                        "category", "category_name", "tuya_functions",
                        "pet_feeder_feed_dp", "pet_feeder_feed_kind",
                        "pet_feeder_clean_hopper_dp", "pet_feeder_clean_hopper_value",
                    ):
                        if normalized.get(key) not in (None, "", [], {}):
                            existing[key] = normalized[key]
                    self._devices[dev_id] = existing
                    imported.append(existing)
                else:
                    self._devices[dev_id] = normalized
                    imported.append(normalized)
            except Exception as err:
                _LOGGER.warning("Failed to import device %s: %s", config.get("device_id", "?"), err)
        if imported:
            await self.async_save()
        return imported

    async def remove(self, device_id: str) -> bool:
        if not device_id:
            return False
        removed = self._devices.pop(device_id, None) is not None
        if removed:
            await self.async_save()
        return removed

    def update_ip(self, device_id: str, ip: str) -> bool:
        """Actualizar IP en memoria (sin guardar). Retorna True si el device existe."""
        if device_id not in self._devices:
            return False
        self._devices[device_id]["host"] = ip
        self._devices[device_id]["ip"] = ip
        return True
