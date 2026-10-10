"""Smoke tests executed against the real Home Assistant Core 2026.10 source."""

import importlib

import homeassistant.core  # Initialize Core's voluptuous compatibility layer first.
from homeassistant import const
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.cover import CoverEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity


def test_exact_core_target():
    assert (const.MAJOR_VERSION, const.MINOR_VERSION, str(const.PATCH_VERSION)) == (2026, 10, "0")


def test_all_platform_modules_import_with_core_2026_10():
    platforms = (
        "alarm_control_panel", "binary_sensor", "button", "climate", "cover", "fan",
        "humidifier", "light", "lock", "number", "select", "sensor", "switch", "text", "vacuum",
    )
    for platform in platforms:
        importlib.import_module(f"custom_components.omni_tuya_local.{platform}")


def test_representative_entities_use_core_entity_contracts():
    from custom_components.omni_tuya_local.binary_sensor import OmniTuyaBinarySensor
    from custom_components.omni_tuya_local.cover import OmniTuyaCover
    from custom_components.omni_tuya_local.sensor import OmniTuyaSensor
    from custom_components.omni_tuya_local.switch import OmniTuyaSwitch

    assert issubclass(OmniTuyaBinarySensor, BinarySensorEntity)
    assert issubclass(OmniTuyaCover, CoverEntity)
    assert issubclass(OmniTuyaSensor, SensorEntity)
    assert issubclass(OmniTuyaSwitch, SwitchEntity)
