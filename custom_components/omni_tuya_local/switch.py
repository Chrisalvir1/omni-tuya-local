from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, HOMEKIT_SWITCH_TYPES
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "switch":
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
        if self._homekit_type == "switch" and self.dps_id == "3":
            # Comederos de mascotas suelen requerir un INT (número de porciones) en lugar de True
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), 1)
            # Revertimos estado interno porque es un botón de una sola acción
            self.async_write_ha_state()
        else:
            await self.coordinator.async_set_status(self.device_id, True, int(self.dps_id))

    async def async_turn_off(self, **kwargs) -> None:
        if not (self._homekit_type == "switch" and self.dps_id == "3"):
            await self.coordinator.async_set_status(self.device_id, False, int(self.dps_id))


_PREDEFINED_SWITCHES: dict[str, list[tuple[str, str | None]]] = {
    "pet_feeder": [("3", "Alimentar ahora")],
    "coffee_maker": [("1", "Preparar café")],
    "kettle": [("1", "Hervir")],
}

def _switch_dps(config: dict, coordinator: OmniTuyaLocalCoordinator) -> list[tuple[str, str | None]]:
    """Determinar qué DPS exponer como canales de switch.

    Orden de prioridad:
    1. dps_map explícito del usuario
    2. DPS predefinidos por device_type
    3. DPS booleanos detectados en el último poll
    4. Fallback al canal 1
    """
    dps_map = config.get("dps_map") or {}
    channels: list[tuple[str, str | None]] = []
    device_type = config.get("device_type") or "generic"

    # 1. dps_map explícito
    for dps_id, desc in dps_map.items():
        if str(dps_id).isdigit():
            name = desc.get("name") if isinstance(desc, dict) else None
            channels.append((str(dps_id), name))

    # 2. DPS predefinidos
    if not channels and device_type in _PREDEFINED_SWITCHES:
        for dps_id, name in _PREDEFINED_SWITCHES[device_type]:
            channels.append((str(dps_id), name))

    # 3. DPS booleanos del último poll (auto-detectar canales)
    if not channels:
        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
        for dps_id, value in raw_dps.items():
            if isinstance(value, bool) and str(dps_id).isdigit():
                existing = next((c for c in channels if c[0] == str(dps_id)), None)
                if existing is None:
                    channels.append((str(dps_id), None))

    # 4. Fallback
    if not channels:
        channels.append(("1", None))

    return sorted(channels, key=lambda item: int(item[0]))
