from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity
from .pet_feeder import pet_feeder_clean_hopper

# ── Mapeo device_type → botones con DPS y nombre ────────────────────────────
# El pet feeder NO tiene un tipo de entidad específico en HomeKit,
# pero con botones bien nombrados la experiencia en HA y HomeKit es óptima.
_DEVICE_BUTTONS: dict[str, list[dict[str, Any]]] = {
    "pet_feeder": [
        # There is no universal Tuya DP for emptying/cleaning a hopper.  This
        # button is created only when the product function schema declares it.
    ],
    "ir_remote": [
        {"dps_id": "1", "name": "Encender/Apagar", "dps_value": "power", "icon": "mdi:power"},
    ],
    "robot_vacuum": [
        {"dps_id": "1", "name": "Iniciar limpieza",    "dps_value": True,  "icon": "mdi:robot-vacuum"},
        {"dps_id": "3", "name": "Volver a base",       "dps_value": "chargego", "icon": "mdi:home-import-outline"},
    ],
    "coffee_maker": [
        {"dps_id": "1", "name": "Preparar café",       "dps_value": True, "icon": "mdi:coffee"},
    ],
    "kettle": [
        {"dps_id": "1", "name": "Hervir",              "dps_value": True, "icon": "mdi:kettle"},
    ],
    "alarm_kit": [
        {"dps_id": "113", "alt_dps_ids": ["123", "1"], "name": "Pánico / SOS", "dps_value": "sos", "icon": "mdi:alert-decagram"},
    ],
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            domain = config.get("domain")
            device_type = config.get("device_type") or "generic"
            dps_map = config.get("dps_map") or {}

            if domain == "button":
                if dps_map:
                    # Crear un botón por cada DPS en el mapa
                    for dps_id, desc in dps_map.items():
                        d = desc if isinstance(desc, dict) else {}
                        uid = f"{DOMAIN}_{config['device_id']}_btn_{dps_id}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            entities.append(OmniTuyaButton(coordinator, config, str(dps_id), d))
                elif device_type in _DEVICE_BUTTONS:
                    # Crear botones predefinidos por device_type
                    for btn in _DEVICE_BUTTONS[device_type]:
                        dps_id = btn["dps_id"]
                        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
                        found_id = None
                        if str(dps_id) in raw_dps:
                            found_id = dps_id
                        else:
                            for alt in btn.get("alt_dps_ids", []):
                                if str(alt) in raw_dps:
                                    found_id = alt
                                    break
                        if found_id is None:
                            found_id = dps_id

                        uid = f"{DOMAIN}_{config['device_id']}_btn_{found_id}_{btn['name']}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            entities.append(
                                OmniTuyaButton(
                                    coordinator, config,
                                    str(found_id),
                                    {"name": btn["name"], "icon": btn.get("icon"), "value": btn.get("dps_value", True)},
                                )
                            )
                else:
                    # Botón genérico DPS 1
                    uid = f"{DOMAIN}_{config['device_id']}_btn"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaButton(coordinator, config, "1", {}))
            else:
                # Si no es button, igual agregamos los botones secundarios predefinidos
                if device_type in _DEVICE_BUTTONS:
                    for btn in _DEVICE_BUTTONS[device_type]:
                        dps_id = btn["dps_id"]
                        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
                        found_id = None
                        if str(dps_id) in raw_dps:
                            found_id = dps_id
                        else:
                            for alt in btn.get("alt_dps_ids", []):
                                if str(alt) in raw_dps:
                                    found_id = alt
                                    break
                        if found_id is None:
                            found_id = dps_id

                        uid = f"{DOMAIN}_{config['device_id']}_btn_{found_id}_{btn['name']}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            entities.append(
                                OmniTuyaButton(
                                    coordinator, config,
                                    str(found_id),
                                    {"name": btn["name"], "icon": btn.get("icon"), "value": btn.get("dps_value", True)},
                                )
                            )

            # This is independent of the primary entity domain.  It also keeps
            # a feeder imported as a switch from accidentally losing its clean
            # action just because the primary export domain changes.
            if device_type == "pet_feeder":
                clean = pet_feeder_clean_hopper(config)
                if clean:
                    dps_id, value = clean
                    uid = f"{DOMAIN}_{config['device_id']}_btn_{dps_id}_clean_hopper"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaButton(
                            coordinator, config, dps_id,
                            {"name": "Limpiar tolva", "icon": "mdi:broom", "value": value},
                        ))

        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()

    # Agregar el botón global de sincronización
    async_add_entities([OmniTuyaSyncCloudButton(coordinator, entry.entry_id)])


class OmniTuyaSyncCloudButton(ButtonEntity):
    """Botón global para sincronizar dispositivos desde la nube Tuya."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-sync"

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, entry_id: str) -> None:
        self.coordinator = coordinator
        self.entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_sync_cloud"
        self._attr_name = "Sincronizar Nube"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "hub")},
            "name": "Omni Tuya Local Hub",
            "manufacturer": "Omni Tuya Local",
            "model": "Integration Hub",
        }

    async def async_press(self) -> None:
        """Activar la sincronización con la nube."""
        await self.coordinator.hass.services.async_call(DOMAIN, "sync_cloud", {})


class OmniTuyaButton(OmniTuyaEntity, ButtonEntity):
    """Botón Tuya (alimentar, limpiar, encender, etc.)."""

    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str = "1",
        desc: dict | None = None,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._desc = desc or {}
        self._dps_value = self._desc.get("value", True)
        uid_suffix = f"_{dps_id}_{self._desc.get('name', '')}" if self._desc.get("name") else f"_{dps_id}"
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_btn{uid_suffix}"
        if self._desc.get("icon"):
            self._attr_icon = self._desc["icon"]

    @property
    def name(self) -> str | None:
        if self._desc.get("name"):
            return self._desc["name"]
        if self.dps_id == "1":
            return None
        return f"Botón {self.dps_id}"

    async def async_press(self) -> None:
        """Activar el botón."""
        value = self._dps_value
        current_val = self.dps(self.dps_id)

        # Conversión dinámica para comandos de pánico en alarmas
        if isinstance(value, str) and value == "sos":
            if isinstance(current_val, bool):
                value = True
            elif str(current_val).upper() in ("ON", "OFF"):
                value = "ON"

        # Conversión dinámica para el botón Volver a base
        if self._desc.get("name") == "Volver a base" and self.dps_id == "1":
            value = "Charge"

        if isinstance(value, str):
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), value)
        elif isinstance(value, int) and not isinstance(value, bool):
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), value)
        else:
            # Para booleanos, si es Pánico/SOS enviamos True permanente (se apaga desarmando)
            if self._desc.get("name") == "Pánico / SOS":
                await self.coordinator.async_set_status(self.device_id, value if isinstance(value, bool) else True, int(self.dps_id))
            else:
                await self.coordinator.async_set_status(self.device_id, True, int(self.dps_id))
                await asyncio.sleep(0.25)
                await self.coordinator.async_set_status(self.device_id, False, int(self.dps_id))
