from __future__ import annotations

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

_DPS_CONTROL = "1"     # open / close / stop
_DPS_PERCENT = "3"     # posición 0-100


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "cover":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaCover(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaCover(OmniTuyaEntity, CoverEntity):
    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self._has_position_dps():
            features |= CoverEntityFeature.SET_POSITION
        return features

    def _has_position_dps(self) -> bool:
        return _DPS_PERCENT in self.raw_dps or _DPS_PERCENT in (self.config.get("dps_map") or {})

    @property
    def is_closed(self) -> bool | None:
        # Primero verificar posición si existe
        if self._has_position_dps():
            pos = self.current_cover_position
            if pos is not None:
                return pos == 0
        value = self.dps(_DPS_CONTROL)
        if value is None:
            return None
        return value in ("close", "closed", False, 0)

    @property
    def is_opening(self) -> bool | None:
        value = self.dps(_DPS_CONTROL)
        if value is None:
            return None
        return value == "open"

    @property
    def is_closing(self) -> bool | None:
        value = self.dps(_DPS_CONTROL)
        if value is None:
            return None
        return value == "close"

    @property
    def current_cover_position(self) -> int | None:
        """Posición actual 0-100."""
        if not self._has_position_dps():
            return None
        value = self.dps(_DPS_PERCENT)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def async_open_cover(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.device_id, int(_DPS_CONTROL), "open")

    async def async_close_cover(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.device_id, int(_DPS_CONTROL), "close")

    async def async_stop_cover(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.device_id, int(_DPS_CONTROL), "stop")

    async def async_set_cover_position(self, **kwargs) -> None:
        """Mover a posición específica (0-100)."""
        if _DPS_PERCENT in kwargs or ATTR_POSITION in kwargs:
            pos = kwargs.get(ATTR_POSITION, 50)
            await self.coordinator.async_set_value(self.device_id, int(_DPS_PERCENT), int(pos))
