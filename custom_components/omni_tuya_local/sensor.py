from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

try:
    from homeassistant.const import UnitOfDensity
    _UNIT_UG_M3: str = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
except (ImportError, AttributeError):
    _UNIT_UG_M3 = "µg/m³"

try:
    from homeassistant.const import UnitOfRatio
    _UNIT_PPM: str = UnitOfRatio.PARTS_PER_MILLION
except (ImportError, AttributeError):
    _UNIT_PPM = "ppm"

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
    "pm25_sensor": (SensorDeviceClass.PM25, _UNIT_UG_M3, SensorStateClass.MEASUREMENT),

    # CO2
    "co2_sensor": (SensorDeviceClass.CO2, _UNIT_PPM, SensorStateClass.MEASUREMENT),

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

from .pet_feeder import function_id

_DPS_PROFILES: dict[str, tuple[SensorDeviceClass | None, str | None, SensorStateClass | None]] = {
    # Telemetría estándar consumo tomacorrientes / interruptores inteligentes (cz, pc, sp)
    "17": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "18": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "19": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "20": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    # Códigos Tuya Cloud y variantes de energía
    "cur_power": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_power_1": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_power_2": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_power_3": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_power_4": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "power": (SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
    "cur_current": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_current_1": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_current_2": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_current_3": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_current_4": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "current": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.MILLIAMPERE, SensorStateClass.MEASUREMENT),
    "cur_voltage": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "voltage": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "add_ele": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "add_ele_1": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "add_ele_2": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "energy": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    "total_forward_energy": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
    # Sensor temp+humedad estándar Tuya (wsdcg)
    "temp": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "hum": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "humidity": (SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "temperature": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "illuminance": (SensorDeviceClass.ILLUMINANCE, "lx", SensorStateClass.MEASUREMENT),
    "co2": (SensorDeviceClass.CO2, _UNIT_PPM, SensorStateClass.MEASUREMENT),
    "pm25": (SensorDeviceClass.PM25, _UNIT_UG_M3, SensorStateClass.MEASUREMENT),
    "battery": (SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "battery_percentage": (SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT),
}


def _is_energy_capable_device(config: dict[str, Any], raw_dps: dict[str, Any]) -> bool:
    dev_type = str(config.get("device_type") or "").lower()
    cat = str(config.get("category") or "").lower()
    product = str(config.get("product_name") or "").lower()
    name = str(config.get("name") or "").lower()

    if cat in ("cz", "pc", "sp", "dlq", "tdq"):
        return True
    if dev_type in ("outlet", "power_strip"):
        return True
    if any(w in product or w in name for w in ("plug", "outlet", "socket", "tomacorriente", "enchufe", "power strip", "regleta", "duo", "breaker", "medidor")):
        return True
    for func in config.get("tuya_functions") or []:
        if isinstance(func, dict):
            code = str(func.get("code") or func.get("identifier") or "").lower()
            if code in ("cur_power", "cur_voltage", "cur_current", "add_ele", "phase_a"):
                return True
    # Si reporta DPS 17-20 con valores numéricos válidos (ej. enchufe o medidor sin metadata)
    if isinstance(raw_dps, dict):
        for dp_key in ("17", "18", "19", "20", 17, 18, 19, 20):
            val = raw_dps.get(dp_key)
            if val is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
                return True
    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            configured_dps: set[str] = set()
            dps_map = config.get("dps_map") or {}

            # 1. Procesar sensores definidos en dps_map
            if config.get("domain") == "sensor" and not dps_map:
                dps_map = {"1": {"name": config.get("name"), "unit": None}}

            for dps_id, desc in dps_map.items():
                dps_id = str(dps_id)
                if not dps_id.isdigit():
                    continue
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

            # 2. Extraer sensores de energía y funciones desde Tuya Cloud (tuya_functions)
            raw_dps = (coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
            if not raw_dps and coordinator.devices.get(config.get("device_id")):
                raw_dps = coordinator.devices[config.get("device_id")].dps
            if not isinstance(raw_dps, dict):
                raw_dps = {}

            tuya_functions = config.get("tuya_functions") or []
            for func in tuya_functions:
                if not isinstance(func, dict):
                    continue
                dp_id = function_id(func)
                if not dp_id or dp_id in configured_dps:
                    continue
                code = str(func.get("code") or func.get("identifier") or "").lower()
                func_type = str(func.get("type") or "").lower()
                is_sensor_func = (
                    code in _DPS_PROFILES
                    or any(k in code for k in ("power", "voltage", "current", "energy", "temp", "hum", "co2", "pm25", "lux", "battery"))
                    or func_type in ("integer", "value", "numeric")
                )
                if is_sensor_func and not code.startswith("switch") and code not in ("mode", "count_down"):
                    configured_dps.add(dp_id)
                    lbl = func.get("name") or func.get("code")
                    name = str(lbl).replace("_", " ").strip().title() if lbl else dps_label(config, dp_id)
                    uid = f"{DOMAIN}_{config['device_id']}_{dp_id}"
                    if uid not in _known_unique_ids:
                        _known_unique_ids.add(uid)
                        entities.append(
                            OmniTuyaSensor(
                                coordinator, config, dp_id, {"name": name, "code": code}
                            )
                        )

            # 3. Telemetría de energía estándar para dispositivos compatibles (enchufes, regletas, relés, etc.)
            if _is_energy_capable_device(config, raw_dps):
                for energy_dp, default_name, code in (
                    ("19", "Potencia", "cur_power"),
                    ("20", "Voltaje", "cur_voltage"),
                    ("18", "Corriente", "cur_current"),
                    ("17", "Energía", "add_ele"),
                ):
                    if energy_dp not in configured_dps:
                        configured_dps.add(energy_dp)
                        uid = f"{DOMAIN}_{config['device_id']}_{energy_dp}"
                        if uid not in _known_unique_ids:
                            _known_unique_ids.add(uid)
                            entities.append(
                                OmniTuyaSensor(
                                    coordinator, config, energy_dp, {"name": default_name, "code": code}
                                )
                            )

            # 4. Todos los valores numéricos/texto observados en LAN (discovered_dps)
            for dps_id, info in discovered_dps(config).items():
                if info["kind"] not in {"number", "text"} or dps_id in configured_dps:
                    continue
                configured_dps.add(dps_id)
                uid = f"{DOMAIN}_{config['device_id']}_{dps_id}"
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
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_{dps_id}"
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

        # 3. Perfil basado en el ID / nombre / código del DPS
        dps_name = str(dps_id).lower()
        desc_code = str(desc.get("code") or "").lower()
        match_key = None
        if desc_code and desc_code in _DPS_PROFILES:
            match_key = desc_code
        elif dps_name in ("17", "18", "19", "20"):
            # Solo asignar perfil de energía si el dispositivo es capaz de medir energía
            raw_dps = (self.coordinator.data or {}).get("dps", {}).get(config.get("device_id"), {})
            if _is_energy_capable_device(config, raw_dps):
                match_key = dps_name
        elif dps_name in _DPS_PROFILES:
            match_key = dps_name

        if not match_key:
            for func in config.get("tuya_functions") or []:
                if isinstance(func, dict) and function_id(func) == str(dps_id):
                    code = str(func.get("code") or func.get("identifier") or "").lower()
                    if code in _DPS_PROFILES:
                        match_key = code
                        break

        if match_key and match_key in _DPS_PROFILES:
            dc, unit, sc = _DPS_PROFILES[match_key]
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

        # 5. Perfil basado en categoría Tuya
        category = (config.get("category") or "").lower()
        profile_key = _CATEGORY_PROFILES.get(category)
        if profile_key and profile_key in _SENSOR_PROFILES:
            dc, unit, sc = _SENSOR_PROFILES[profile_key]
            self._attr_device_class = dc
            self._attr_native_unit_of_measurement = explicit_unit or unit
            self._attr_state_class = sc
            return

        # 6. Fallback: unidad del desc o None
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
        if str(self.dps_id) == "19":
            return "Potencia"
        if str(self.dps_id) == "20":
            return "Voltaje"
        if str(self.dps_id) == "18":
            return "Corriente"
        if str(self.dps_id) == "17":
            return "Energía"
        if self.dps_id == "1":
            return None
        return f"Sensor {self.dps_id}"

    @property
    def native_value(self):
        value = self.dps(self.dps_id)
        if value is None and self._desc.get("code"):
            value = self.dps(self._desc["code"])
        if value is None:
            for func in self.config.get("tuya_functions") or []:
                if isinstance(func, dict) and str(function_id(func)) == str(self.dps_id):
                    code = func.get("code") or func.get("identifier")
                    if code:
                        value = self.dps(code)
                        if value is not None:
                            break
        if value is None:
            return None

        # Limpiar strings vacíos o nulos
        if isinstance(value, str):
            val_clean = value.strip()
            if not val_clean or val_clean.lower() in ("none", "null", "unknown", "unavailable"):
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
                return round(float(value) / 10.0, 1)
            except (TypeError, ValueError):
                return None
        # Si es voltaje y viene en décimas de V
        if self._attr_device_class == SensorDeviceClass.VOLTAGE:
            try:
                v = float(value)
                return round(v / 10.0, 1) if v > 500 else round(v, 1)
            except (TypeError, ValueError):
                return None
        # Si es corriente eléctrica (mA)
        if self._attr_device_class == SensorDeviceClass.CURRENT:
            try:
                return round(float(value), 1)
            except (TypeError, ValueError):
                return None
        # Si es energía acumulada (kWh)
        if self._attr_device_class == SensorDeviceClass.ENERGY:
            try:
                v = float(value)
                # Escalar según formato estándar Tuya (centésimas de kWh)
                if self._attr_native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR and v > 500:
                    return round(v / 100.0, 3)
                return round(v, 3)
            except (TypeError, ValueError):
                return None

        # Para cualquier sensor con unidad de medida o clase de estado numérica, validar que sea convertible
        if (
            self._attr_state_class is not None
            or self._attr_native_unit_of_measurement is not None
            or self._attr_device_class is not None
        ):
            try:
                v = float(value)
                return int(v) if v.is_integer() else v
            except (TypeError, ValueError):
                return None

        return value
