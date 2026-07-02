from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

# ── Mapeo device_type → BinarySensorDeviceClass ──────────────────────────────
# Esto es LO MÁS IMPORTANTE para que HomeKit identifique correctamente
# los sensores como Motion, Contact, Smoke, Leak, etc.
_DEVICE_TYPE_TO_CLASS: dict[str, BinarySensorDeviceClass] = {
    # Movimiento / presencia
    "motion_sensor": BinarySensorDeviceClass.MOTION,
    "presence_sensor": BinarySensorDeviceClass.PRESENCE,

    # Puerta / ventana / contacto
    "door_sensor": BinarySensorDeviceClass.DOOR,
    "window_sensor": BinarySensorDeviceClass.WINDOW,
    "garage_door": BinarySensorDeviceClass.GARAGE_DOOR,

    # Humo / gas / CO
    "smoke_sensor": BinarySensorDeviceClass.SMOKE,
    "gas_sensor": BinarySensorDeviceClass.GAS,
    "co_sensor": BinarySensorDeviceClass.CO,

    # Agua / humedad
    "water_leak_sensor": BinarySensorDeviceClass.MOISTURE,

    # Vibración / tamper
    "vibration_sensor": BinarySensorDeviceClass.VIBRATION,
    "tamper_sensor": BinarySensorDeviceClass.TAMPER,

    # Batería baja
    "battery_sensor": BinarySensorDeviceClass.BATTERY,

    # Conectividad
    "connectivity_sensor": BinarySensorDeviceClass.CONNECTIVITY,
}

# Mapeo categoría Tuya → device_class (para auto-detección desde nube)
_CATEGORY_TO_CLASS: dict[str, BinarySensorDeviceClass] = {
    "pir": BinarySensorDeviceClass.MOTION,
    "mcs": BinarySensorDeviceClass.DOOR,
    "cs": BinarySensorDeviceClass.DOOR,
    "ywbj": BinarySensorDeviceClass.SMOKE,
    "rqbj": BinarySensorDeviceClass.GAS,
    "sjcj": BinarySensorDeviceClass.MOISTURE,
    "ldcg": BinarySensorDeviceClass.PRESENCE,
}

# ── Entidades predefinidas para alarm_kit (alarma solar multizona) ────────────
# Cada tupla: (dps_id, nombre, device_class, unique_suffix)
# DPS 106 = trigger PIR solar (movimiento detectado — push efímero)
# DPS 102 = zona activa del selector físico en el sensor
# DPS 109-112 = zonas 1-4 habilitadas (read-only, refleja switch físico en base)
# DPS 119 = tamper / antisabotaje
_ALARM_KIT_SENSORS: list[tuple[str, str, BinarySensorDeviceClass, str]] = [
    ("106", "Sensor Solar",  BinarySensorDeviceClass.MOTION,  "pir"),
    ("102", "Zona Activa",   BinarySensorDeviceClass.SAFETY,  "zone_active"),
    ("109", "Zona 1",        BinarySensorDeviceClass.SAFETY,  "zone1"),
    ("110", "Zona 2",        BinarySensorDeviceClass.SAFETY,  "zone2"),
    ("111", "Zona 3",        BinarySensorDeviceClass.SAFETY,  "zone3"),
    ("112", "Zona 4",        BinarySensorDeviceClass.SAFETY,  "zone4"),
    ("119", "Antisabotaje",  BinarySensorDeviceClass.TAMPER,  "tamper"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "binary_sensor":
                continue

            device_type = config.get("device_type") or ""

            if device_type == "alarm_kit":
                # Crear una entidad binary_sensor por cada DPS del alarm_kit
                for dps_id, sensor_name, device_class, suffix in _ALARM_KIT_SENSORS:
                    uid = f"{DOMAIN}_{config['device_id']}_bs_{suffix}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(
                            OmniTuyaAlarmBinarySensor(
                                coordinator, config, dps_id, sensor_name, device_class, suffix
                            )
                        )
            else:
                uid = f"{DOMAIN}_{config['device_id']}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(OmniTuyaBinarySensor(coordinator, config))

        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaBinarySensor(OmniTuyaEntity, BinarySensorEntity):
    """Sensor binario Tuya con device_class automático para HomeKit."""

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict) -> None:
        super().__init__(coordinator, config, "1")
        # Determinar device_class: prioridad: config explícita > device_type > categoría
        explicit = config.get("device_class")
        if explicit and hasattr(BinarySensorDeviceClass, explicit.upper()):
            self._attr_device_class = BinarySensorDeviceClass(explicit.lower())
        else:
            device_type = config.get("device_type") or ""
            category = config.get("category") or ""
            self._attr_device_class = (
                _DEVICE_TYPE_TO_CLASS.get(device_type)
                or _CATEGORY_TO_CLASS.get(category.lower())
            )

    @property
    def is_on(self) -> bool | None:
        value = self.dps("1")
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "on", "open", "motion", "detected",
                                       "wet", "smoke", "gas", "alarm"}


class OmniTuyaAlarmBinarySensor(OmniTuyaEntity, BinarySensorEntity):
    """Binary sensor para un DPS específico de un alarm_kit (alarma solar multizona).

    Permite exponer individualmente: sensor PIR solar (DPS 106), zonas habilitadas
    (DPS 109-112), zona activa del selector físico (DPS 102) y tamper (DPS 119).
    Todas son read-only — el hardware controla su estado físicamente.
    """

    def __init__(
        self,
        coordinator: OmniTuyaLocalCoordinator,
        config: dict,
        dps_id: str,
        sensor_name: str,
        device_class: BinarySensorDeviceClass,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._sensor_name = sensor_name
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_bs_{unique_suffix}"

    @property
    def name(self) -> str:
        return self._sensor_name

    @property
    def is_on(self) -> bool | None:
        value = self.dps(self.dps_id)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "on", "open", "motion",
                                       "detected", "alarm", "active"}
