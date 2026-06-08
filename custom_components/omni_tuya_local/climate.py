from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

# DPS convencionales Tuya para clima
_DPS_POWER = "1"
_DPS_MODE = "2"
_DPS_TEMP_CURRENT = "3"
_DPS_TEMP_TARGET = "4"
_DPS_FAN_SPEED = "5"
_DPS_PRESET = "8"

_TUYA_TO_HA_MODE = {
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "auto": HVACMode.AUTO,
    "fan_only": HVACMode.FAN_ONLY,
    "dry": HVACMode.DRY,
}
_HA_TO_TUYA_MODE = {v: k for k, v in _TUYA_TO_HA_MODE.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "climate":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaClimate(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaClimate(OmniTuyaEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_WHOLE
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.AUTO,
        HVACMode.FAN_ONLY,
        HVACMode.DRY,
    ]
    _attr_fan_modes = ["auto", "low", "medium", "high"]
    _attr_preset_modes = ["none", "eco", "sleep", "boost", "away"]

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict) -> None:
        super().__init__(coordinator, config, "1")
        dps_map = config.get("dps_map") or {}
        # Temperaturas mín/máx configurables desde dps_map o defaults seguros
        self._attr_min_temp = float(
            (dps_map.get("temp_min") or {}).get("value", 16)
            if isinstance(dps_map.get("temp_min"), dict)
            else dps_map.get("temp_min", 16)
        )
        self._attr_max_temp = float(
            (dps_map.get("temp_max") or {}).get("value", 30)
            if isinstance(dps_map.get("temp_max"), dict)
            else dps_map.get("temp_max", 30)
        )

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        if self.dps(_DPS_FAN_SPEED) is not None:
            features |= ClimateEntityFeature.FAN_MODE
        if self.dps(_DPS_PRESET) is not None:
            features |= ClimateEntityFeature.PRESET_MODE
        return features

    @property
    def hvac_mode(self) -> HVACMode:
        power = self.dps(_DPS_POWER)
        if power is False or power == "off" or power == "false":
            return HVACMode.OFF
        mode = str(self.dps(_DPS_MODE) or "auto").lower()
        return _TUYA_TO_HA_MODE.get(mode, HVACMode.AUTO)

    @property
    def current_temperature(self) -> float | None:
        val = self.dps(_DPS_TEMP_CURRENT)
        if val is None:
            return None
        try:
            return float(val) / 10 if float(val) > 100 else float(val)
        except (TypeError, ValueError):
            return None

    @property
    def target_temperature(self) -> float | None:
        val = self.dps(_DPS_TEMP_TARGET)
        if val is None:
            return None
        try:
            return float(val) / 10 if float(val) > 100 else float(val)
        except (TypeError, ValueError):
            return None

    @property
    def fan_mode(self) -> str | None:
        return self.dps(_DPS_FAN_SPEED)

    @property
    def preset_mode(self) -> str | None:
        val = self.dps(_DPS_PRESET)
        return str(val) if val is not None else "none"

    async def async_set_temperature(self, **kwargs) -> None:
        if "temperature" in kwargs:
            val = kwargs["temperature"]
            await self.coordinator.async_set_value(self.device_id, int(_DPS_TEMP_TARGET), int(val))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_status(self.device_id, False, 1)
            return
        tuya_mode = _HA_TO_TUYA_MODE.get(hvac_mode, "auto")
        await self.coordinator.async_set_values(
            self.device_id,
            {1: True, int(_DPS_MODE): tuya_mode}
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.coordinator.async_set_value(self.device_id, int(_DPS_FAN_SPEED), fan_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == "none":
            return
        await self.coordinator.async_set_value(self.device_id, int(_DPS_PRESET), preset_mode)
