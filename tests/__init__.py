"""Tests for Omni Tuya Local."""
import sys
from unittest.mock import MagicMock

class DummyEntity:
    _attr_has_entity_name = True
    _attr_unique_id = None
    _attr_name = None
    _attr_device_info = None
    _attr_device_class = None
    _attr_native_unit_of_measurement = None
    _attr_state_class = None
    _attr_entity_category = None

    def __class_getitem__(cls, item):
        return cls
    
    @property
    def extra_state_attributes(self):
        return {}

class DummyCoordinatorEntity(DummyEntity):
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator

for mod_name in [
    "voluptuous",
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.alarm_control_panel",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.button",
    "homeassistant.components.climate",
    "homeassistant.components.cover",
    "homeassistant.components.diagnostics",
    "homeassistant.components.fan",
    "homeassistant.components.humidifier",
    "homeassistant.components.light",
    "homeassistant.components.lock",
    "homeassistant.components.number",
    "homeassistant.components.persistent_notification",
    "homeassistant.components.select",
    "homeassistant.components.sensor",
    "homeassistant.components.switch",
    "homeassistant.components.text",
    "homeassistant.components.vacuum",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.event",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.percentage",
    "tinytuya",
]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = MagicMock()

# Override base classes to avoid metaclass conflicts
for comp, entity_names in [
    ("sensor", ["SensorEntity"]),
    ("switch", ["SwitchEntity"]),
    ("light", ["LightEntity"]),
    ("button", ["ButtonEntity"]),
    ("climate", ["ClimateEntity"]),
    ("fan", ["FanEntity"]),
    ("humidifier", ["HumidifierEntity"]),
    ("number", ["NumberEntity"]),
    ("select", ["SelectEntity"]),
    ("text", ["TextEntity"]),
    ("vacuum", ["StateVacuumEntity"]),
    ("binary_sensor", ["BinarySensorEntity"]),
    ("cover", ["CoverEntity"]),
    ("lock", ["LockEntity"]),
    ("alarm_control_panel", ["AlarmControlPanelEntity"]),
]:
    m = sys.modules[f"homeassistant.components.{comp}"]
    for attr in entity_names:
        setattr(m, attr, DummyEntity)

sensor_mod = sys.modules["homeassistant.components.sensor"]

class SensorDeviceClass:
    BATTERY = "battery"
    CURRENT = "current"
    DURATION = "duration"
    ENERGY = "energy"
    POWER = "power"
    VOLTAGE = "voltage"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    ILLUMINANCE = "illuminance"
    CO2 = "co2"
    PM25 = "pm25"
    SIGNAL_STRENGTH = "signal_strength"

class SensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"

sensor_mod.SensorDeviceClass = SensorDeviceClass
sensor_mod.SensorStateClass = SensorStateClass

coord_mod = sys.modules["homeassistant.helpers.update_coordinator"]
coord_mod.CoordinatorEntity = DummyCoordinatorEntity

entity_mod = sys.modules["homeassistant.helpers.entity"]
entity_mod.Entity = DummyEntity
entity_mod.DeviceInfo = dict

const_mod = sys.modules["homeassistant.const"]
const_mod.PERCENTAGE = "%"

class UnitOfPower:
    WATT = "W"
    KILO_WATT = "kW"

class UnitOfEnergy:
    KILO_WATT_HOUR = "kWh"
    WATT_HOUR = "Wh"

class UnitOfElectricCurrent:
    MILLIAMPERE = "mA"
    AMPERE = "A"

class UnitOfElectricPotential:
    VOLT = "V"

class UnitOfTemperature:
    CELSIUS = "°C"
    FAHRENHEIT = "°F"

const_mod.UnitOfPower = UnitOfPower
const_mod.UnitOfEnergy = UnitOfEnergy
const_mod.UnitOfElectricCurrent = UnitOfElectricCurrent
const_mod.UnitOfElectricPotential = UnitOfElectricPotential
const_mod.UnitOfTemperature = UnitOfTemperature
