from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .dps import dps_label
from .entity import OmniTuyaEntity
from .pet_feeder import function_id

# ── Opciones predefinidas por device_type ────────────────────────────────────
# Si no hay opciones en dps_map, usamos estas como fallback
_DEVICE_TYPE_OPTIONS: dict[str, list[str]] = {
    "air_purifier": ["auto", "sleep", "low", "medium", "high"],
    # Tuya's ``sd`` (robot vacuum) profile.  These are protocol values, not
    # translated labels: the device only accepts the exact value below.
    "robot_vacuum": [
        "standby", "random", "smart", "wall_follow", "spiral", "chargego",
    ],
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

_PREDEFINED_SELECTS: dict[str, list[dict[str, Any]]] = {
    "alarm_kit": [
        {"dps_id": "115", "name": "Sonido Zona 1", "options": ["clock", "bark", "bell", "dingdong", "alarm", "doorbell", "beep", "silent"]},
        {"dps_id": "116", "name": "Sonido Zona 2", "options": ["clock", "bark", "bell", "dingdong", "alarm", "doorbell", "beep", "silent"]},
        {"dps_id": "117", "name": "Sonido Zona 3", "options": ["clock", "bark", "bell", "dingdong", "alarm", "doorbell", "beep", "silent"]},
        {"dps_id": "118", "name": "Sonido Zona 4", "options": ["clock", "bark", "bell", "dingdong", "alarm", "doorbell", "beep", "silent"]},
    ]
}

# Mapeo de DPS 'mode' típicos de Tuya según category
_CATEGORY_OPTIONS: dict[str, list[str]] = {
    "kj": ["auto", "sleep", "low", "medium", "high"],  # air purifier
    "sd": _DEVICE_TYPE_OPTIONS["robot_vacuum"],  # robot vacuum
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
            device_domain = config.get("domain")
            device_type = config.get("device_type") or "generic"
            # Vacuum mode is a regular HA Select even though the device itself
            # lives in the vacuum domain.  Previously this condition skipped
            # every robot vacuum, leaving the Mode DP visible only as a
            # read-only generic sensor.
            if (
                device_domain not in {"select", "vacuum"}
                and device_type not in _PREDEFINED_SELECTS
            ):
                continue

            is_vacuum = (
                device_domain == "vacuum"
                or device_type == "robot_vacuum"
                or (config.get("category") or "").lower() == "sd"
            )

            # Determinar DPS de modo y opciones disponibles
            dps_map = config.get("dps_map") or {}
            if dps_map:
                # A vacuum's custom map can also contain telemetry labels. Its
                # only select is the documented mode DP, never every mapped
                # value. Preserve the generic behaviour for select devices.
                mapped_items = (
                    [("3", dps_map.get("3", {"name": "Modo de limpieza"}))]
                    if is_vacuum
                    else dps_map.items()
                )
                for dps_id, desc in mapped_items:
                    uid = f"{DOMAIN}_{config['device_id']}_select_{dps_id}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaSelect(coordinator, config, str(dps_id), desc))
            elif device_type in _PREDEFINED_SELECTS:
                for item in _PREDEFINED_SELECTS[device_type]:
                    dps_id = item["dps_id"]
                    uid = f"{DOMAIN}_{config['device_id']}_select_{dps_id}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaSelect(coordinator, config, str(dps_id), item))
            else:
                # Standard Tuya robot vacuums use DP 3 for ``mode``.  Other
                # select-only devices retain the historical generic DP 2.
                dps_id = "3" if is_vacuum else "2"
                uid = f"{DOMAIN}_{config['device_id']}_select_{dps_id}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(
                        OmniTuyaSelect(
                            coordinator,
                            config,
                            dps_id,
                            {"name": "Modo de limpieza"} if dps_id == "3" else {},
                        )
                    )

            if is_vacuum:
                # The "Manual" tile in Smart Life is not another DP 3 mode.
                # It opens a directional pad backed by DP 4.  A select gives
                # HA an explicit control, and HomeKit Bridge maps it to a
                # power strip with one button per direction.
                manual_dps_id = "4"
                uid = f"{DOMAIN}_{config['device_id']}_select_{manual_dps_id}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(
                        OmniTuyaSelect(
                            coordinator,
                            config,
                            manual_dps_id,
                            {
                                "name": "Control manual",
                                "options": [
                                    "forward", "backward", "turn_left",
                                    "turn_right", "stop",
                                ],
                            },
                        )
                    )

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
        if not explicit_options:
            explicit_options = _function_options(config, dps_id)
        if explicit_options and isinstance(explicit_options, list):
            self._base_options = [str(o) for o in explicit_options]
        else:
            device_type = config.get("device_type") or ""
            category = (config.get("category") or "").lower()
            self._base_options = (
                _DEVICE_TYPE_OPTIONS.get(device_type)
                or _CATEGORY_OPTIONS.get(category)
                or ["auto", "manual", "off"]
            )

    @property
    def name(self) -> str | None:
        if self._desc.get("name"):
            return self._desc["name"]
        return dps_label(self.config, self.dps_id)

    @property
    def options(self) -> list[str]:
        opts = list(self._base_options)
        curr = self.current_option
        if curr and curr not in opts:
            opts.append(curr)
        return opts

    @property
    def current_option(self) -> str | None:
        value = self.dps(self.dps_id)
        if value is None:
            return None
        return str(value)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_value(self.device_id, int(self.dps_id), option)


def _function_options(config: dict, dps_id: str) -> list[str] | None:
    """Read enum choices from the product schema fetched from Tuya Cloud.

    Tuya returns the allowed enum range in a JSON string in some API versions
    and as a mapping in others.  Prefer that product-specific schema over the
    standard ``sd`` fallback, so unsupported modes are never offered.
    """
    for function in config.get("tuya_functions") or []:
        if not isinstance(function, dict) or function_id(function) != str(dps_id):
            continue
        values = function.get("values")
        if isinstance(values, str):
            import json

            try:
                values = json.loads(values)
            except (TypeError, ValueError):
                continue
        if not isinstance(values, dict):
            continue
        options = values.get("range")
        if isinstance(options, list) and all(isinstance(option, (str, int, float)) for option in options):
            return [str(option) for option in options]
    return None
