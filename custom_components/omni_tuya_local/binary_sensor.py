from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .dps import discovered_dps
from .entity import OmniTuyaEntity
from .light import _light_dps
from .switch import _switch_dps

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
# DPS 101 = trigger PIR solar (movimiento detectado — push efímero, false=detectado)
# DPS 102 = zona activa del selector físico en el sensor
# DPS 109-112 = zonas 1-4 habilitadas (read-only, refleja switch físico en base)
# DPS 119 = tamper / antisabotaje
_ALARM_KIT_SENSORS: list[tuple[str, str, BinarySensorDeviceClass, str]] = [
    ("101", "Sensor Solar",  BinarySensorDeviceClass.MOTION,  "pir"),
    ("106", "Sensor Solar (106)", BinarySensorDeviceClass.MOTION, "pir_106"),
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
            device_domain = config.get("domain")
            device_type = config.get("device_type") or ""

            # Keep the dedicated primary entities for binary-sensor products
            # and alarm kits, then add LAN-discovered booleans below for every
            # other product type as read-only entities.
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
            elif device_domain == "binary_sensor":
                uid = f"{DOMAIN}_{config['device_id']}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(OmniTuyaBinarySensor(coordinator, config))

            if device_type == "alarm_kit":
                continue

            # Show every boolean DPS observed over LAN as a read-only binary
            # sensor.  The primary binary sensor above keeps its existing
            # stable unique_id, so it is not duplicated here.
            switch_dps_ids = {
                dps_id for dps_id, _ in _switch_dps(config, coordinator)
            } if (device_domain == "switch" or device_type in {"pet_feeder", "coffee_maker", "kettle", "outlet", "power_strip", "switch"}) else set()

            light_dps_ids = {
                dps_id for dps_id, _ in _light_dps(config, coordinator)
            } if device_domain == "light" else set()

            for dps_id, info in discovered_dps(config).items():
                if info["kind"] != "boolean":
                    continue
                if device_domain == "binary_sensor" and dps_id == "1":
                    continue
                if dps_id in switch_dps_ids or dps_id in light_dps_ids:
                    continue
                if device_domain in {
                    "switch", "light", "fan", "cover", "climate", "lock",
                    "vacuum", "humidifier", "alarm_control_panel",
                } and str(dps_id).isdigit() and int(dps_id) in range(1, 9):
                    continue
                uid = f"{DOMAIN}_{config['device_id']}_dps_{dps_id}_binary"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(
                        OmniTuyaDiscoveredBinarySensor(
                            coordinator, config, dps_id, info["name"]
                        )
                    )

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


class OmniTuyaDiscoveredBinarySensor(OmniTuyaEntity, BinarySensorEntity):
    """A safely observed boolean DPS not covered by the primary platform."""

    def __init__(
        self, coordinator: OmniTuyaLocalCoordinator, config: dict,
        dps_id: str, name: str,
    ) -> None:
        super().__init__(coordinator, config, dps_id)
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_dps_{dps_id}_binary"
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        value = self.dps(self.dps_id)
        if value is None:
            return None
        return value is True or str(value).lower() in {
            "1", "true", "on", "open", "motion", "detected", "wet", "smoke", "gas", "alarm",
        }


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
        self._last_trigger_time: float = 0.0

    @property
    def name(self) -> str:
        return self._sensor_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.dps_id in ("101", "106"):
            value = self.dps(self.dps_id)
            push_time = self.dps(f"_push_time_{self.dps_id}")
            
            if value is not None and push_time is not None and push_time > self._last_trigger_time:
                is_triggered = False
                if isinstance(value, bool):
                    is_triggered = not value
                else:
                    is_triggered = str(value).lower() in {"0", "false", "off", "closed"}
                    
                if is_triggered:
                    self._last_trigger_time = push_time
                    # Auto-reset el estado después de 3.5 segundos para HomeKit
                    self.hass.loop.call_later(3.5, self.async_write_ha_state)
                    
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool | None:
        if self.dps_id in ("101", "106"):
            import time
            # Latch de 3.5 segundos para la UI y automations (HomeKit)
            if time.time() - self._last_trigger_time < 3.5:
                return True
            return False

        value = self.dps(self.dps_id)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "on", "open", "motion",
                                       "detected", "alarm", "active"}
