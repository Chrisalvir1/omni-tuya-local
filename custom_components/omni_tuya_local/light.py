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
from .dps import dps_label
from .entity import OmniTuyaEntity
from .pet_feeder import function_id
from .util import ha_to_tuya_brightness, tuya_to_ha_brightness


def _light_dps(config: dict, coordinator: OmniTuyaLocalCoordinator) -> list[tuple[str, str | None]]:
    """Determinar qué DPS exponer como canales de luz."""
    channels_dict: dict[str, str | None] = {}
    dps_map = config.get("dps_map") or {}
    tuya_functions = config.get("tuya_functions") or []
    disc_dps = config.get("discovered_dps") or {}
    raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
    if not raw_dps and coordinator.devices.get(config.get("device_id")):
        raw_dps = coordinator.devices[config.get("device_id")].dps

    # 1. dps_map explícito
    for dps_id, desc in dps_map.items():
        if str(dps_id).isdigit():
            name = desc.get("name") if isinstance(desc, dict) else (desc if isinstance(desc, str) else None)
            channels_dict[str(dps_id)] = name

    # 2. tuya_functions (esquema Tuya Cloud)
    for func in tuya_functions:
        if not isinstance(func, dict):
            continue
        dp_id = function_id(func)
        if not dp_id or not dp_id.isdigit():
            continue
        code = str(func.get("code") or func.get("identifier") or "").lower()
        if code in ("switch", "switch_led", "power") or code.startswith("switch_") or code.startswith("led_"):
            name = func.get("name") or func.get("code")
            if name:
                name = str(name).replace("_", " ").strip().title()
            if dp_id not in channels_dict or not channels_dict[dp_id]:
                channels_dict[dp_id] = name

    # 3. discovered_dps persistido en config (canales 1..8)
    for dps_id, info in disc_dps.items():
        if str(dps_id).isdigit() and isinstance(info, dict) and info.get("kind") == "boolean":
            if int(dps_id) in range(1, 9) and str(dps_id) not in channels_dict:
                lbl = info.get("name")
                channels_dict[str(dps_id)] = lbl if lbl and lbl != f"DPS {dps_id}" else None

    # 4. raw_dps en vivo (canales 1..8)
    for dps_id, value in raw_dps.items():
        if isinstance(value, bool) and str(dps_id).isdigit() and int(dps_id) in range(1, 9):
            if str(dps_id) not in channels_dict:
                channels_dict[str(dps_id)] = None

    if not channels_dict:
        channels_dict["1"] = None

    sorted_channels = sorted(channels_dict.items(), key=lambda item: int(item[0]))
    has_multiple = len(sorted_channels) > 1
    result: list[tuple[str, str | None]] = []
    for dps_id, name in sorted_channels:
        if name:
            result.append((dps_id, name))
        elif has_multiple:
            label = dps_label(config, dps_id)
            if label and label != f"DPS {dps_id}":
                result.append((dps_id, label))
            else:
                result.append((dps_id, f"Luz {dps_id}"))
        else:
            result.append((dps_id, None))
    return result


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "light":
                continue
            for dps_id, name in _light_dps(config, coordinator):
                unique_suffix = "" if dps_id == "1" else f"_{dps_id}"
                uid = f"{DOMAIN}_{config['device_id']}{unique_suffix}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(OmniTuyaLight(coordinator, config, dps_id, name))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


def _first_valid_dps(entity: OmniTuyaEntity, *keys: str | int) -> Any:
    for k in keys:
        val = entity.dps(k)
        if val is not None:
            return val
    return None


class OmniTuyaLight(OmniTuyaEntity, LightEntity):
    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str = "1",
        channel_name: str | None = None,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._channel_name = channel_name

    @property
    def current_power_w(self) -> float | None:
        """Return current power consumption in watts."""
        val = _first_valid_dps(self, "19", "cur_power", "power", "cur_power_1")
        if val is not None:
            try:
                return round(float(val) / 10.0, 1)
            except (TypeError, ValueError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes

        # Telemetría de energía para HomeKit (Eve Energy / Home+) y Home Assistant
        power_val = _first_valid_dps(self, "19", "cur_power", "power", "cur_power_1")
        if power_val is not None:
            try:
                p = round(float(power_val) / 10.0, 1)
                attrs["current_power_w"] = p
                attrs["power"] = p
            except (TypeError, ValueError):
                pass

        voltage_val = _first_valid_dps(self, "20", "cur_voltage", "voltage")
        if voltage_val is not None:
            try:
                v = float(voltage_val)
                attrs["voltage"] = round(v / 10.0, 1) if v > 500 else round(v, 1)
            except (TypeError, ValueError):
                pass

        current_val = _first_valid_dps(self, "18", "cur_current", "current", "cur_current_1")
        if current_val is not None:
            try:
                c = float(current_val)
                attrs["current_a"] = round(c / 1000.0, 3)
                attrs["current_ma"] = round(c, 1)
                attrs["current"] = attrs["current_a"]
            except (TypeError, ValueError):
                pass

        energy_val = _first_valid_dps(self, "17", "add_ele", "energy", "total_forward_energy", "add_ele_1")
        if energy_val is not None:
            try:
                e = float(energy_val)
                attrs["total_energy_kwh"] = round(e / 100.0, 3) if e > 500 else round(e, 3)
                attrs["energy"] = attrs["total_energy_kwh"]
            except (TypeError, ValueError):
                pass

        return attrs

    @property
    def name(self) -> str | None:
        if self._channel_name:
            return self._channel_name
        if self.dps_id == "1":
            return None
        return f"Luz {self.dps_id}"

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
        if not self._has_dps(DPS_HSV):
            return False
        raw = self.dps(DPS_HSV)
        if raw is not None and not isinstance(raw, str):
            return False
        return True

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
        if not self._has_dps(DPS_COLOR_TEMP):
            return False
        raw = self.dps(DPS_COLOR_TEMP)
        if raw is not None:
            if isinstance(raw, str) and not raw.isdigit():
                return False
        return True

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
        value = self.dps(self.dps_id)
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
        payload_dps: dict[int, Any] = {int(self.dps_id): True}

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
        await self.coordinator.async_set_status(self.device_id, False, int(self.dps_id))


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
