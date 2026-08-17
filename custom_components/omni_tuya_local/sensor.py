from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .dps import discovered_dps, dps_label
from .entity import OmniTuyaEntity

# ── Mapeo device_type/category → (SensorDeviceClass, unit, state_class) ──────
# Con esto HomeKit Bridge crea los accesorios correctos para temperatura,
# humedad, etc. y la UI de HA muestra las unidades y gráficas adecuadas.
_SENSOR_PROFILES: dict[str, tuple[SensorDeviceClass | None, str | None, SensorStateClass | None]] = {
    # Temperatura
    "temperature_sensor": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "wsdcg_temp": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),

    # Humedad
    "humidity_sensor": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "wsdcg_hum": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),

    # Iluminancia (lux)
    "illuminance_sensor": (SensorDeviceClass.ILLUMINANCE, "lx", SensorStateClass.MEASUREMENT),
    "cgq": (SensorDeviceClass.ILLUMINANCE, "lx", SensorStateClass.MEASUREMENT),

    # PM2.5 / calidad del aire
    "pm25_sensor": (SensorDeviceClass.PM25, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorStateClass.MEASUREMENT),

    # CO2
    "co2_sensor": (SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, SensorStateClass.MEASUREMENT),

    # Energía / potencia (tomacorriente inteligente)
    "power_sensor": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "energy_sensor": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "current_sensor": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "voltage_sensor": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),

    # Batería
    "battery": (SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT),

    # Señal
    "signal_strength": (SensorDeviceClass.SIGNAL_STRENGTH, "dBm", SensorStateClass.MEASUREMENT),
}

# Categorías Tuya → perfil
_CATEGORY_PROFILES: dict[str, str] = {
    "wsdcg": "temperature_sensor",  # Se expande a temp + hum en DPS múltiples
    "cgq": "cgq",
    "pm25": "pm25_sensor",
    "co2bj": "co2_sensor",
}

_ROBOT_VACUUM_DPS_PROFILES: dict[str, tuple[SensorDeviceClass | None, str | None, SensorStateClass | None]] = {
    "6": (SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "7": (None, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "8": (None, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "9": (None, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "17": (SensorDeviceClass.DURATION, "min", SensorStateClass.MEASUREMENT),
}

_DPS_PROFILES: dict[str, tuple[SensorDeviceClass | None, str | None, SensorStateClass | None]] = {
    # Telemetría estándar consumo tomacorrientes / interruptores inteligentes (cz, pc, sp)
    "17": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "18": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "19": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "20": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    # Sensor temp+humedad estándar Tuya (wsdcg)
    "temp": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "hum": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "humidity": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "temperature": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "illuminance": (SensorDeviceClass.ILLUMINANCE, "lx", SensorStateClass.MEASUREMENT),
    "co2": (SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, SensorStateClass.MEASUREMENT),
    "pm25": (SensorDeviceClass.PM25, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorStateClass.MEASUREMENT),
    "cur_power": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_current": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_voltage": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "add_ele": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            configured_dps: set[str] = set()
            if config.get("domain") != "sensor":
                dps_map = {}
            else:
                dps_map = config.get("dps_map") or {
                    "1": {"name": config.get("name"), "unit": None}
                }
                for dps_id, desc in dps_map.items():
                    dps_id = str(dps_id)
                    configured_dps.add(dps_id)
                    uid = f"{DOMAIN}_{config['device_id']}_{dps_id}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(
                            OmniTuyaSensor(
                                coordinator, config, dps_id,
                                desc if isinstance(desc, dict) else {}
                            )
                        )

            # Every numeric/text value actually observed on the LAN is exposed
            # read-only.  Unknown Tuya DPS are deliberately sensors, not
            # controls, so a product-specific command is never guessed.
            for dps_id, info in discovered_dps(config).items():
                if info["kind"] not in {"number", "text"} or dps_id in configured_dps:
                    continue
                uid = f"{DOMAIN}_{config['device_id']}_dps_{dps_id}"
                if uid not in _known_unique_ids:
                    _known_unique_ids.add(uid)
                    entities.append(
                        OmniTuyaSensor(
                            coordinator, config, dps_id, {"name": info["name"]}
                        )
                    )
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaSensor(OmniTuyaEntity, SensorEntity):
    """Sensor numérico Tuya con device_class y unidades automáticas para HomeKit."""

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict, dps_id: str, desc: dict) -> None:
        super().__init__(coordinator, config, dps_id)
        self._desc = desc
        self._resolve_class_and_unit(config, dps_id, desc)

    def _resolve_class_and_unit(self, config: dict, dps_id: str, desc: dict) -> None:
        """Determinar device_class, unit y state_class de mayor a menor prioridad."""
        # 1. Clase explícita en desc (dps_map)
        explicit_class = desc.get("device_class")
        explicit_unit = desc.get("unit")

        if explicit_class and hasattr(SensorDeviceClass, explicit_class.upper()):
            self._attr_device_class = SensorDeviceClass(explicit_class.lower())
            self._attr_native_unit_of_measurement = explicit_unit
            self._attr_state_class = SensorStateClass.MEASUREMENT
            return

        # 2. Perfil para robot aspirador
        device_type = (config.get("device_type") or "").lower()
        category = (config.get("category") or "").lower()
        domain = (config.get("domain") or "").lower()
        if (device_type == "robot_vacuum" or category == "sd" or domain == "vacuum") and str(dps_id) in _ROBOT_VACUUM_DPS_PROFILES:
            dc, unit, sc = _ROBOT_VACUUM_DPS_PROFILES[str(dps_id)]
            self._attr_device_class = dc
            self._attr_native_unit_of_measurement = explicit_unit or unit
            self._attr_state_class = sc
            return

        # 3. Perfil basado en el ID / nombre del DPS
        dps_name = str(dps_id).lower()
        if dps_name in _DPS_PROFILES:
            dc, unit, sc = _DPS_PROFILES[dps_name]
            self._attr_device_class = dc
            self._attr_native_unit_of_measurement = explicit_unit or unit
            self._attr_state_class = sc
            return

        # 4. Perfil basado en device_type del config
        if device_type in _SENSOR_PROFILES:
            dc, unit, sc = _SENSOR_PROFILES[device_type]
            self._attr_device_class = dc
            self._attr_native_unit_of_measurement = explicit_unit or unit
            self._attr_state_class = sc
            return

        # 4. Perfil basado en categoría Tuya
        category = (config.get("category") or "").lower()
        profile_key = _CATEGORY_PROFILES.get(category)
        if profile_key and profile_key in _SENSOR_PROFILES:
            dc, unit, sc = _SENSOR_PROFILES[profile_key]
            self._attr_device_class = dc
            self._attr_native_unit_of_measurement = explicit_unit or unit
            self._attr_state_class = sc
            return

        # 5. Fallback: unidad del desc o None
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = explicit_unit
        self._attr_state_class = SensorStateClass.MEASUREMENT if explicit_unit else None

    @property
    def name(self) -> str | None:
        if self._desc.get("name"):
            return self._desc["name"]
        label = dps_label(self.config, self.dps_id)
        if label and label != f"DPS {self.dps_id}":
            return label
        if self.dps_id == "1":
            return None
        return f"Sensor {self.dps_id}"

    @property
    def native_value(self):
        value = self.dps(self.dps_id)
        if value is None:
            return None
        # Si el device_class es temperatura y el valor viene en décimas, convertir
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            try:
                v = float(value)
                return v / 10 if v > 100 else v
            except (TypeError, ValueError):
                return None
        # Si es potencia y viene en décimas de W
        if self._attr_device_class == SensorDeviceClass.POWER:
            try:
                return float(value) / 10
            except (TypeError, ValueError):
                return value
        # Si es voltaje y viene en décimas de V
        if self._attr_device_class == SensorDeviceClass.VOLTAGE:
            try:
                v = float(value)
                return v / 10 if v > 500 else v
            except (TypeError, ValueError):
                return value
        return value
