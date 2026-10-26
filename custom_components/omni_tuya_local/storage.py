from __future__ import annotations

import asyncio
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import normalize_device

_LOGGER = logging.getLogger(__name__)


class TuyaDeviceStore:
    """The integration-wide, durable device inventory.

    A config entry is created for each Tuya device, but they all represent the
    same cloud account and therefore must share one inventory.  Keeping a
    store object per entry used to cause concurrent startup writes to replace
    each other with stale snapshots of ``.storage``.
    """

    def __new__(cls, hass: HomeAssistant):
        domain_data = hass.data.setdefault("omni_tuya_local", {})
        existing = domain_data.get("_device_store")
        if existing is not None:
            return existing
        instance = super().__new__(cls)
        domain_data["_device_store"] = instance
        return instance

    def __init__(self, hass: HomeAssistant) -> None:
        # __init__ is invoked even when __new__ returns the cached instance.
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._devices: dict[str, dict] = {}
        self.cloud_config: dict = {}
        self._loaded = False
        self._load_lock = asyncio.Lock()
        self._mutation_lock = asyncio.Lock()

    async def async_load(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:
                return
            data = await self._store.async_load() or {}
            raw_devices = data.get("devices") or {}
            loaded: dict[str, dict] = {}
            for dev_id, config in raw_devices.items():
                # Validar que el device_id no esté vacío (Bug #7)
                real_id = config.get("device_id") or dev_id
                if not real_id or not str(real_id).strip():
                    _LOGGER.warning("Skipping stored device with empty device_id (key=%s)", dev_id)
                    continue
                config = dict(config)
                config.setdefault("device_id", real_id)
                try:
                    normalized = normalize_device(config)
                    loaded[normalized["device_id"]] = normalized
                except Exception as err:
                    _LOGGER.warning("Could not load stored device %s: %s", dev_id, err)
            self._devices = loaded
            self.cloud_config = dict(data.get("cloud_config") or {})
            self._loaded = True

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
        async with self._mutation_lock:
            normalized = normalize_device(config)
            dev_id = normalized.get("device_id", "")
            if not dev_id or not str(dev_id).strip():
                raise ValueError("Cannot add device with empty device_id")
            self._devices[dev_id] = normalized
            await self.async_save()
            return normalized

    async def add_many(self, configs: list[dict]) -> list[dict]:
        async with self._mutation_lock:
            imported = []
            for config in configs:
                try:
                    normalized = normalize_device(config)
                    dev_id = normalized.get("device_id", "")
                    if not dev_id or not str(dev_id).strip():
                        _LOGGER.warning("Skipping device with empty device_id during bulk import")
                        continue
                    # Merge if exists. Smart Life may call the same physical
                    # device by a virtual/cloud ID while LAN discovery reports
                    # a gwId. Match their stable aliases before creating a
                    # duplicate device or ignoring a renamed device.
                    existing_id = self._matching_device_id(normalized)
                    if existing_id:
                        existing = self._devices[existing_id]
                        # Cloud data may refresh the local key and product schema,
                        # but it must never discard local IP/discovery state or the
                        # user's persisted serving preference.
                        for key in (
                            "name", "local_key", "product_name", "product_id",
                            "category", "category_name", "tuya_functions",
                            "cloud_id", "uuid", "mac",
                            "initial_dps",
                            "pet_feeder_feed_dp", "pet_feeder_feed_kind",
                            "pet_feeder_clean_hopper_dp", "pet_feeder_clean_hopper_value",
                        ):
                            if normalized.get(key) not in (None, "", [], {}):
                                existing[key] = normalized[key]
                        # Keep Home Assistant's stable inventory/entity ID,
                        # while talking to the current Tuya LAN ID after a
                        # factory reset or transfer to another Smart Life account.
                        existing["lan_device_id"] = normalized.get("device_id") or existing_id
                        self._devices[existing_id] = existing
                        imported.append(existing)
                    else:
                        normalized.setdefault("lan_device_id", dev_id)
                        self._devices[dev_id] = normalized
                        imported.append(normalized)
                except Exception as err:
                    _LOGGER.warning("Failed to import device %s: %s", config.get("device_id", "?"), err)
            if imported:
                await self.async_save()
            return imported

    def _matching_device_id(self, incoming: dict) -> str | None:
        """Find a stored device using direct or cloud/LAN stable identities."""
        direct_id = str(incoming.get("device_id") or "")
        if direct_id in self._devices:
            return direct_id
        cloud_id = str(incoming.get("cloud_id") or "")
        if cloud_id in self._devices:
            return cloud_id
        aliases = {value for value in (direct_id, cloud_id) if value}
        matches = [stored_id for stored_id, stored in self._devices.items() if aliases.intersection({stored.get("lan_device_id"), stored.get("cloud_id")})]
        if len(matches) == 1:
            return matches[0]

        # A factory reset/account transfer may assign a new cloud ID and local
        # key to the same physical device. Match by UUID or MAC, in that order;
        # a local key is a credential and can rotate, so it is not an identity.
        for identity in ("uuid", "mac"):
            value = str(incoming.get(identity) or "").strip().lower()
            if not value:
                continue
            if identity == "mac":
                value = "".join(char for char in value if char in "0123456789abcdef")
                if len(value) != 12:
                    continue
            matches = []
            for stored_id, stored in self._devices.items():
                stored_value = str(stored.get(identity) or "").strip().lower()
                if identity == "mac":
                    stored_value = "".join(
                        char for char in stored_value if char in "0123456789abcdef"
                    )
                    if len(stored_value) != 12:
                        continue
                if value == stored_value:
                    matches.append(stored_id)
            if len(matches) == 1:
                _LOGGER.info(
                    "Matched Tuya cloud identity %s by %s to stored device %s",
                    direct_id or "?", identity, matches[0],
                )
                return matches[0]
            if len(matches) > 1:
                _LOGGER.warning(
                    "Ambiguous Tuya %s match for cloud device %s; keeping it separate",
                    identity, direct_id or "?",
                )
                return None
        return None

    async def remove(self, device_id: str) -> bool:
        if not device_id:
            return False
        async with self._mutation_lock:
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
