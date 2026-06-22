from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DPS_BRIGHTNESS,
    DPS_COLOR_TEMP,
    DPS_HSV,
    DPS_MODE,
    TUYA_BRIGHTNESS_MAX,
    TUYA_BRIGHTNESS_MIN,
    TUYA_COLOR_TEMP_MAX,
    TUYA_COLOR_TEMP_MIN,
)
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity
from .util import ha_to_tuya_brightness, tuya_to_ha_brightness


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "light":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaLight(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaLight(OmniTuyaEntity, LightEntity):
    """Luz Tuya con detección dinámica de ColorMode."""

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict) -> None:
        super().__init__(coordinator, config, "1")

    # ── Detección dinámica de capacidades ─────────────────────────────────────

    def _has_dps(self, dps_id: str) -> bool:
        """Verificar si un DPS existe en los datos del device (poll o dps_map)."""
        raw_dps = self.raw_dps
        if dps_id in raw_dps:
            return True
        dps_map = self.config.get("dps_map") or {}
        return dps_id in dps_map

    @property
    def _supports_hs_color(self) -> bool:
        return self._has_dps(DPS_HSV)

    @property
    def _brightness_dps(self) -> str | None:
        """Determinar dinámicamente el DPS de brillo (Tuya usa 3, 2 o 22)."""
        dps_map = self.config.get("dps_map") or {}
        for k, v in dps_map.items():
            if v == "brightness":
                return str(k)

        dps_2 = self.dps("2")
        # En dimmers (como ELEGRP), DPS 2 es el brillo real (int) y DPS 3 es el límite mínimo.
        # En bombillos RGB estándar, DPS 2 es modo ("white", "colour") y DPS 3 es brillo.
        if self._has_dps("2") and isinstance(dps_2, int):
            return "2"

        for dps in (DPS_BRIGHTNESS, "22"):
            if self._has_dps(dps):
                return dps
        return None

    @property
    def _supports_brightness(self) -> bool:
        return self._brightness_dps is not None

    @property
    def _supports_color_temp(self) -> bool:
        return self._has_dps(DPS_COLOR_TEMP)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        modes: set[ColorMode] = set()
        if self._supports_hs_color:
            modes.add(ColorMode.HS)
        if self._supports_color_temp:
            modes.add(ColorMode.COLOR_TEMP)
        if not modes and self._supports_brightness:
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        return modes

    @property
    def color_mode(self) -> ColorMode:
        if self._supports_hs_color:
            mode_val = str(self.dps(DPS_MODE) or "").lower()
            if mode_val == "colour" or not self._supports_color_temp:
                return ColorMode.HS
            return ColorMode.COLOR_TEMP
        if self._supports_color_temp:
            return ColorMode.COLOR_TEMP
        if self._supports_brightness:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    # ── Estado ────────────────────────────────────────────────────────────────

    @property
    def is_on(self) -> bool | None:
        value = self.dps("1")
        if value is None:
            return None
        return value is True or value == "on"

    @property
    def brightness(self) -> int | None:
        dps_id = self._brightness_dps
        if not dps_id:
            return None
        value = self.dps(dps_id)
        if value is None:
            return None
        try:
            return tuya_to_ha_brightness(int(value))
        except (TypeError, ValueError):
            return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        if not self._supports_hs_color:
            return None
        raw = self.dps(DPS_HSV)
        if raw is None:
            return None
        return _parse_tuya_hsv(raw)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Temperatura de color en Kelvin."""
        if not self._supports_color_temp:
            return None
        value = self.dps(DPS_COLOR_TEMP)
        if value is None:
            return None
        try:
            # Convertir 0-1000 a mireds (153-500) y luego a Kelvin
            normalized = int(value) / TUYA_COLOR_TEMP_MAX
            mireds = 500 - normalized * (500 - 153)
            return int(1000000 / mireds)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @property
    def min_color_temp_kelvin(self) -> int:
        return 2000  # 1000000 / 500 mireds

    @property
    def max_color_temp_kelvin(self) -> int:
        return 6535  # 1000000 / 153 mireds

    # ── Comandos ──────────────────────────────────────────────────────────────

    async def async_turn_on(self, **kwargs: Any) -> None:
        payload_dps: dict[int, Any] = {1: True}

        dps_bright = self._brightness_dps
        if ATTR_BRIGHTNESS in kwargs and dps_bright:
            tuya_bright = ha_to_tuya_brightness(kwargs[ATTR_BRIGHTNESS])
            payload_dps[int(dps_bright)] = tuya_bright

        if ATTR_HS_COLOR in kwargs and self._supports_hs_color:
            hs = kwargs[ATTR_HS_COLOR]
            hsv_hex = _ha_hs_to_tuya_hsv(hs[0], hs[1])
            payload_dps[int(DPS_HSV)] = hsv_hex
            payload_dps[int(DPS_MODE)] = "colour"

        elif ATTR_COLOR_TEMP_KELVIN in kwargs and self._supports_color_temp:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            # Convertir Kelvin a mireds (mireds = 1000000 / kelvin)
            mireds = 1000000 / kelvin
            # Convertir mireds (153-500) → 0-1000
            normalized = (500 - mireds) / (500 - 153)
            tuya_ct = int(max(0, min(TUYA_COLOR_TEMP_MAX, normalized * TUYA_COLOR_TEMP_MAX)))
            payload_dps[int(DPS_COLOR_TEMP)] = tuya_ct
            if self._supports_hs_color:
                payload_dps[int(DPS_MODE)] = "white"

        await self.coordinator.async_set_values(self.device_id, payload_dps)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_status(self.device_id, False, 1)


# ─── Helpers de color ─────────────────────────────────────────────────────────

def _parse_tuya_hsv(raw: Any) -> tuple[float, float] | None:
    """Parsear HSV Tuya (hex 12 chars o dict) a (hue, saturation) de HA."""
    try:
        if isinstance(raw, str) and len(raw) == 12:
            # Formato: HHHHSSSSVVVV (hue 0-360, sat 0-1000, val 0-1000, 4 chars cada uno)
            h = int(raw[0:4], 16)
            s = int(raw[4:8], 16)
            # v = int(raw[8:12], 16)  # no lo necesitamos para hs_color
            hue = h % 360
            sat = min(100.0, s / 10.0)
            return (float(hue), float(sat))
        if isinstance(raw, dict):
            hue = float(raw.get("h", 0)) % 360
            sat = float(raw.get("s", 0)) / 10.0
            return (hue, min(100.0, sat))
    except (ValueError, TypeError):
        pass
    return None


def _ha_hs_to_tuya_hsv(hue: float, saturation: float, value: int = 1000) -> str:
    """Convertir (hue, saturation) de HA a hex HHHHSSSSVVVV de Tuya."""
    h = int(hue) % 360
    s = int(saturation * 10)
    v = value
    return f"{h:04x}{s:04x}{v:04x}"
