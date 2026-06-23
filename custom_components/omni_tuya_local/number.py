from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity
from .pet_feeder import pet_feeder_feed

# ── Perfiles predefinidos por device_type (min, max, step, unit) ──────────────
_DEVICE_NUMBER_PROFILES: dict[str, list[dict]] = {
    "pet_feeder": [
        # This is intentionally virtual.  Video feeders use one numeric command
        # DP to feed, so the amount must be selected before pressing Feed now.
        {"dps_id": "virtual_portions", "name": "Porciones por comida", "min": 1, "max": 20, "step": 1, "unit": ""},
    ],
    "alarm_kit": [
        {"dps_id": "41", "name": "Volumen de alarma", "min": 0, "max": 10, "step": 1, "unit": ""},
    ],
    "air_purifier": [
        {"dps_id": "15", "name": "Temporizar apagado",   "min": 0, "max": 480, "step": 30, "unit": "min"},
    ],
    "sprinkler": [
        {"dps_id": "3",  "name": "Duración del riego",   "min": 1, "max": 120, "step": 1,  "unit": "min"},
    ],
    "climate": [
        {"dps_id": "4",  "name": "Temperatura objetivo", "min": 16, "max": 30,  "step": 1, "unit": "°C"},
    ],
    "humidifier": [
        {"dps_id": "2",  "name": "Humedad objetivo",     "min": 30, "max": 80,  "step": 5, "unit": "%"},
    ],
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            domain = config.get("domain")
            dps_map = config.get("dps_map") or {}
            device_type = config.get("device_type") or "generic"

            if domain == "number":
                if dps_map:
                    for dps_id, desc in dps_map.items():
                        d = desc if isinstance(desc, dict) else {}
                        uid = f"{DOMAIN}_{config['device_id']}_num_{dps_id}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            entities.append(OmniTuyaNumber(coordinator, config, str(dps_id), d))
                elif device_type in _DEVICE_NUMBER_PROFILES:
                    for profile in _DEVICE_NUMBER_PROFILES[device_type]:
                        dps_id = profile["dps_id"]
                        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
                        
                        if dps_id == "virtual_portions":
                            if not pet_feeder_feed(config, raw_dps):
                                continue
                            found_id = "virtual_portions"
                        else:
                            found_id = None
                            if str(dps_id) in raw_dps:
                                found_id = dps_id
                            else:
                                for alt in profile.get("alt_dps_ids", []):
                                    if str(alt) in raw_dps:
                                        found_id = alt
                                        break
                            if found_id is None:
                                found_id = dps_id

                        uid = f"{DOMAIN}_{config['device_id']}_num_{found_id}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            p = dict(profile)
                            p["dps_id"] = str(found_id)
                            entities.append(OmniTuyaNumber(coordinator, config, str(found_id), p))
                else:
                    uid = f"{DOMAIN}_{config['device_id']}_num"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(OmniTuyaNumber(coordinator, config, "1", {}))
            else:
                # Si no es el dominio principal, aun así agregamos los perfiles numéricos secundarios si existen
                if device_type in _DEVICE_NUMBER_PROFILES:
                    for profile in _DEVICE_NUMBER_PROFILES[device_type]:
                        dps_id = profile["dps_id"]
                        raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
                        
                        if dps_id == "virtual_portions":
                            if not pet_feeder_feed(config, raw_dps):
                                continue
                            found_id = "virtual_portions"
                        else:
                            found_id = None
                            if str(dps_id) in raw_dps:
                                found_id = dps_id
                            else:
                                for alt in profile.get("alt_dps_ids", []):
                                    if str(alt) in raw_dps:
                                        found_id = alt
                                        break
                            if found_id is None:
                                found_id = dps_id

                        uid = f"{DOMAIN}_{config['device_id']}_num_{found_id}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            p = dict(profile)
                            p["dps_id"] = str(found_id)
                            entities.append(OmniTuyaNumber(coordinator, config, str(found_id), p))

        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaNumber(OmniTuyaEntity, NumberEntity):
    """Entidad numérica editable para valores Tuya como porciones, temperatura, tiempo."""

    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str = "1",
        desc: dict | None = None,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._desc = desc or {}
        uid_suffix = f"_{dps_id}"
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_num{uid_suffix}"

        # Rango configurable desde dps_map o perfil
        self._attr_native_min_value = float(self._desc.get("min", 0))
        self._attr_native_max_value = float(self._desc.get("max", 1000))
        self._attr_native_step = float(self._desc.get("step", 1))
        self._attr_native_unit_of_measurement = self._desc.get("unit")
        self._attr_mode = NumberMode.BOX

    @property
    def name(self) -> str | None:
        if self._desc.get("name"):
            return self._desc["name"]
        if self.dps_id == "1":
            return None
        return f"Número {self.dps_id}"

    @property
    def native_value(self) -> float | None:
        if self.dps_id == "virtual_portions":
            config = self.coordinator.get_device_config(self.device_id) or self.config
            return float(config.get("manual_feed_portions", 1))

        value = self.dps(self.dps_id)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        if self.dps_id == "virtual_portions":
            await self.coordinator.async_set_manual_feed_portions(self.device_id, int(value))
            self.async_write_ha_state()
            return

        # Si el step es entero, enviar int para compatibilidad Tuya
        if self._attr_native_step == int(self._attr_native_step):
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), int(value))
        else:
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), value)
