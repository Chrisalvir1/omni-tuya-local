from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

from .const import DOMAIN, HOMEKIT_FAN_TYPES
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

# DPS convencionales Tuya para ventiladores
_DPS_POWER = "1"
_DPS_SPEED = "3"     # velocidad (puede ser "low"/"medium"/"high" o 1/2/3)
_DPS_OSCILLATE = "8" # oscilación on/off

_SPEED_ORDERED = ["low", "medium", "high"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "fan":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaFan(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaFan(OmniTuyaEntity, FanEntity):
    _attr_speed_count = 3

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict) -> None:
        super().__init__(coordinator, config, "1")
        device_type = config.get("device_type") or "fan"
        self._homekit_fan_type = HOMEKIT_FAN_TYPES.get(device_type, "fan")

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes
        attrs["homekit_type"] = self._homekit_fan_type
        return attrs

    @property
    def name(self) -> str:
        return self.config.get("name") or self.device_id

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature(0)
        if self._has_speed_dps():
            features |= FanEntityFeature.SET_SPEED
        if self._has_oscillate_dps():
            features |= FanEntityFeature.OSCILLATE
        return features

    def _has_speed_dps(self) -> bool:
        return _DPS_SPEED in self.raw_dps or _DPS_SPEED in (self.config.get("dps_map") or {})

    def _has_oscillate_dps(self) -> bool:
        return _DPS_OSCILLATE in self.raw_dps or _DPS_OSCILLATE in (self.config.get("dps_map") or {})

    @property
    def is_on(self) -> bool | None:
        value = self.dps(_DPS_POWER)
        if value is None:
            return None
        return value is True or value == "on"

    @property
    def percentage(self) -> int | None:
        """Velocidad como porcentaje (0-100)."""
        if not self._has_speed_dps():
            return None
        value = self.dps(_DPS_SPEED)
        if value is None:
            return None
        # Si es numérico (1-3)
        try:
            idx = int(value)
            if 1 <= idx <= 3:
                return ordered_list_item_to_percentage(_SPEED_ORDERED, _SPEED_ORDERED[idx - 1])
        except (TypeError, ValueError):
            pass
        # Si es string (low/medium/high)
        if str(value).lower() in _SPEED_ORDERED:
            return ordered_list_item_to_percentage(_SPEED_ORDERED, str(value).lower())
        return None

    @property
    def oscillating(self) -> bool | None:
        if not self._has_oscillate_dps():
            return None
        value = self.dps(_DPS_OSCILLATE)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        payload_dps: dict[int, Any] = {1: True}
        if percentage is not None and self._has_speed_dps():
            speed_str = percentage_to_ordered_list_item(_SPEED_ORDERED, percentage)
            payload_dps[int(_DPS_SPEED)] = speed_str
        await self.coordinator.async_set_values(self.device_id, payload_dps)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_status(self.device_id, False, 1)

    async def async_set_percentage(self, percentage: int) -> None:
        if not self._has_speed_dps():
            return
        speed_str = percentage_to_ordered_list_item(_SPEED_ORDERED, percentage)
        await self.coordinator.async_set_value(self.device_id, int(_DPS_SPEED), speed_str)

    async def async_oscillate(self, oscillating: bool) -> None:
        if self._has_oscillate_dps():
            await self.coordinator.async_set_value(self.device_id, int(_DPS_OSCILLATE), oscillating)
