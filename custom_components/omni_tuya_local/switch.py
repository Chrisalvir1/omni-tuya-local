from __future__ import annotations

import asyncio

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, HOMEKIT_SWITCH_TYPES
from .coordinator import OmniTuyaLocalCoordinator
from .dps import dps_label
from .entity import OmniTuyaEntity
from .pet_feeder import function_id, pet_feeder_feed


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            device_domain = config.get("domain")
            device_type = config.get("device_type") or "generic"
            if (
                device_domain != "switch"
                and device_type not in _PREDEFINED_SWITCHES
                and device_type not in ("outlet", "power_strip", "switch")
            ):
                continue
            for dps_id, name in _switch_dps(config, coordinator):
                unique_suffix = "" if dps_id == "1" else f"_{dps_id}"
                uid = f"{DOMAIN}_{config['device_id']}{unique_suffix}"
                # Deduplicar: no agregar si ya existe (Bug #1)
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(OmniTuyaSwitch(coordinator, config, dps_id, name))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaSwitch(OmniTuyaEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str = "1",
        channel_name: str | None = None,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._channel_name = channel_name
        self._is_feeding = False
        # HomeKit type hint automático según device_type
        device_type = config.get("device_type") or ""
        self._homekit_type = HOMEKIT_SWITCH_TYPES.get(device_type, "switch")

    @property
    def name(self) -> str | None:
        if self._channel_name:
            return self._channel_name
        if self.dps_id == "1":
            return None
        return f"Canal {self.dps_id}"

    @property
    def is_on(self) -> bool | None:
        if self._is_pet_feeder_feed():
            return self._is_feeding
        value = self.dps(self.dps_id)
        if value is None:
            return None
        return value is True or value == "on"

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes
        attrs["homekit_type"] = self._homekit_type
        return attrs

    async def async_turn_on(self, **kwargs) -> None:
        if self._is_pet_feeder_feed():
            # Tuya's video-feeder feed_publish/manual_feed DP is write-only and
            # expects the selected serving count.  Persisted config keeps the
            # choice across HA restarts, IP changes and rediscovery.
            config = self.coordinator.get_device_config(self.device_id) or self.config
            portions = int(config.get("manual_feed_portions", 1))
            _, kind = pet_feeder_feed(config, self.raw_dps) or (self.dps_id, "value")
            
            # Cambiamos estado local a encendido temporalmente
            self._is_feeding = True
            self.async_write_ha_state()

            try:
                if kind == "bool":
                    await self.coordinator.async_set_status(self.device_id, True, int(self.dps_id))
                else:
                    await self.coordinator.async_set_value(self.device_id, int(self.dps_id), portions)
            finally:
                # Esperamos 2 segundos y volvemos a apagar para que en HomeKit se vea como pulsador
                async def auto_reset():
                    await asyncio.sleep(2.0)
                    self._is_feeding = False
                    self.async_write_ha_state()
                self.hass.async_create_task(auto_reset())
        else:
            await self.coordinator.async_set_status(self.device_id, True, int(self.dps_id))

    async def async_turn_off(self, **kwargs) -> None:
        if not self._is_pet_feeder_feed():
            await self.coordinator.async_set_status(self.device_id, False, int(self.dps_id))

    def _is_pet_feeder_feed(self) -> bool:
        config = self.coordinator.get_device_config(self.device_id) or self.config
        selected = pet_feeder_feed(config, self.raw_dps)
        return bool(config.get("device_type") == "pet_feeder" and selected and selected[0] == self.dps_id)


_PREDEFINED_SWITCHES: dict[str, list[dict[str, Any]]] = {
    "pet_feeder": [
        {"name": "Alimentar ahora"},
    ],
    "coffee_maker": [
        {"dps_id": "1", "name": "Preparar café"},
    ],
    "kettle": [
        {"dps_id": "1", "name": "Hervir"},
    ],
}

def _switch_dps(config: dict, coordinator: OmniTuyaLocalCoordinator) -> list[tuple[str, str | None]]:
    """Determinar qué DPS exponer como canales de switch.

    Consolida canales de switch de múltiples fuentes:
    1. Predefinidos para dispositivos especiales (ej. pet_feeder, coffee_maker, kettle)
    2. dps_map explícito del usuario
    3. tuya_functions (esquema Tuya Cloud con funciones booleanas de tipo switch)
    4. discovered_dps persistido en config
    5. raw_dps recibidos en vivo del coordinador
    6. Fallback al canal 1
    """
    device_type = config.get("device_type") or "generic"

    # 1. DPS predefinidos para tipos especiales
    if device_type in _PREDEFINED_SWITCHES:
        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
        feed = pet_feeder_feed(config, raw_dps)
        if feed:
            return [(feed[0], _PREDEFINED_SWITCHES["pet_feeder"][0].get("name", "Alimentar ahora"))]
        predefined = []
        for item in _PREDEFINED_SWITCHES[device_type]:
            dp_id = str(item.get("dps_id", "1"))
            predefined.append((dp_id, item.get("name")))
        if predefined:
            return predefined

    channels_dict: dict[str, str | None] = {}
    dps_map = config.get("dps_map") or {}
    tuya_functions = config.get("tuya_functions") or []
    disc_dps = config.get("discovered_dps") or {}
    raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
    if not raw_dps and coordinator.devices.get(config.get("device_id")):
        raw_dps = coordinator.devices[config.get("device_id")].dps

    # 2. dps_map explícito
    for dps_id, desc in dps_map.items():
        if str(dps_id).isdigit():
            name = desc.get("name") if isinstance(desc, dict) else (desc if isinstance(desc, str) else None)
            channels_dict[str(dps_id)] = name

    # 3. tuya_functions (esquema de funciones desde Tuya Cloud)
    for func in tuya_functions:
        if not isinstance(func, dict):
            continue
        dp_id = function_id(func)
        if not dp_id or not dp_id.isdigit():
            continue
        code = str(func.get("code") or func.get("identifier") or "").lower()
        func_type = str(func.get("type") or "").lower()
        is_switch_code = (
            code in ("switch", "power", "outlet")
            or code.startswith("switch_")
            or code.startswith("power_")
            or code.startswith("outlet_")
            or (func_type in ("boolean", "bool") and "switch" in code)
        )
        if is_switch_code:
            name = func.get("name") or func.get("code")
            if name:
                name = str(name).replace("_", " ").strip().title()
            if dp_id not in channels_dict or not channels_dict[dp_id]:
                channels_dict[dp_id] = name

    # 4. discovered_dps persistido en config (DPS booleanos observados en LAN)
    for dps_id, info in disc_dps.items():
        if not str(dps_id).isdigit():
            continue
        if isinstance(info, dict) and info.get("kind") == "boolean":
            if str(dps_id) not in channels_dict:
                lbl = info.get("name")
                channels_dict[str(dps_id)] = lbl if lbl and lbl != f"DPS {dps_id}" else None

    # 5. raw_dps en vivo (auto-detectar canales booleanos activos en LAN)
    for dps_id, value in raw_dps.items():
        if isinstance(value, bool) and str(dps_id).isdigit():
            if str(dps_id) not in channels_dict:
                channels_dict[str(dps_id)] = None

    # 6. Fallback al canal 1 si no se detectó nada
    if not channels_dict:
        channels_dict["1"] = None

    sorted_channels = sorted(channels_dict.items(), key=lambda item: int(item[0]))

    # Si hay múltiples canales y alguno no tiene nombre explícito, asignar etiqueta estándar
    result: list[tuple[str, str | None]] = []
    has_multiple = len(sorted_channels) > 1
    for dps_id, name in sorted_channels:
        if name:
            result.append((dps_id, name))
        elif has_multiple:
            label = dps_label(config, dps_id)
            if label and label != f"DPS {dps_id}":
                result.append((dps_id, label))
            elif device_type in ("outlet", "power_strip") or str(config.get("category") or "").lower() in ("cz", "pc", "sp"):
                result.append((dps_id, f"Toma {dps_id}"))
            else:
                result.append((dps_id, f"Canal {dps_id}"))
        else:
            result.append((dps_id, None))

    return result
