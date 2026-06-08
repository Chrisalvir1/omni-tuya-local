from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

# ── Opciones predefinidas por device_type ────────────────────────────────────
# Si no hay opciones en dps_map, usamos estas como fallback
_DEVICE_TYPE_OPTIONS: dict[str, list[str]] = {
    "air_purifier": ["auto", "sleep", "low", "medium", "high"],
    "robot_vacuum": ["smart", "random", "gyro", "fast", "wall_follow", "mop", "spiral"],
    "air_conditioner": ["cold", "heat", "wind", "wet", "auto"],
    "humidifier": ["sleep", "low", "medium", "high", "auto"],
    "fan": ["sleep", "low", "medium", "high", "strong"],
    "kettle": ["boiling", "baby_milk", "coffee", "keep_warm", "standby"],
    "coffee_maker": ["americano", "espresso", "cappuccino", "manual"],
    "light": ["white", "colour", "scene", "music"],
    "led_strip": ["white", "colour", "scene", "music"],
    "dimmer": ["white", "colour", "scene"],
    "washer": ["standard", "quick_wash", "delicate", "heavy", "spin", "rinse"],
    "dryer": ["standard", "quick_dry", "heavy", "delicate", "anti_wrinkle"],
    "pet_feeder": ["none"],  # El pet feeder usa button, pero puede tener modo
    "alarm_kit": ["disarmed", "home", "away", "sos"],
    "ir_remote": ["power", "mute", "vol+", "vol-", "ch+", "ch-"],
}

# Mapeo de DPS 'mode' típicos de Tuya según category
_CATEGORY_OPTIONS: dict[str, list[str]] = {
    "kj": ["auto", "sleep", "low", "medium", "high"],  # air purifier
    "sd": ["smart", "random", "gyro", "fast", "wall_follow", "mop"],  # vacuum
    "jsq": ["sleep", "low", "medium", "high", "auto"],  # humidifier
    "fs": ["sleep", "low", "medium", "high"],  # fan
    "kt": ["cold", "heat", "wind", "wet", "auto"],  # AC
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Tuya select entities para selección de modos."""
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "select":
                continue

            # Determinar DPS de modo y opciones disponibles
            dps_map = config.get("dps_map") or {}
            if dps_map:
                # Crear un select por cada DPS en el mapa
                for dps_id, desc in dps_map.items():
                    uid = f"{DOMAIN}_{config['device_id']}_select_{dps_id}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaSelect(coordinator, config, str(dps_id), desc))
            else:
                # Select de modo genérico (DPS 2)
                uid = f"{DOMAIN}_{config['device_id']}_select"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(OmniTuyaSelect(coordinator, config, "2", {}))

        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaSelect(OmniTuyaEntity, SelectEntity):
    """Selector de modo para dispositivos Tuya con múltiples opciones."""

    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str = "2",
        desc: dict | Any = None,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        desc = desc or {}
        self._desc = desc if isinstance(desc, dict) else {}
        unique_suffix = "" if dps_id == "2" else f"_{dps_id}"
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_select{unique_suffix}"

        # Determinar opciones disponibles (desc > device_type > category > fallback genérico)
        explicit_options = self._desc.get("options")
        if explicit_options and isinstance(explicit_options, list):
            self._attr_options = [str(o) for o in explicit_options]
        else:
            device_type = config.get("device_type") or ""
            category = (config.get("category") or "").lower()
            self._attr_options = (
                _DEVICE_TYPE_OPTIONS.get(device_type)
                or _CATEGORY_OPTIONS.get(category)
                or ["auto", "manual", "off"]
            )

    @property
    def name(self) -> str | None:
        if self._desc.get("name"):
            return self._desc["name"]
        return "Modo"

    @property
    def current_option(self) -> str | None:
        value = self.dps(self.dps_id)
        if value is None:
            return None
        return str(value)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_value(self.device_id, int(self.dps_id), option)
