from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfApparentPower, UnitOfFrequency, UnitOfReactivePower

from custom_components.omni_tuya_local.sensor import (
    _DPS_PROFILES,
    _is_extended_profile_reported,
)
from custom_components.omni_tuya_local.valve import OmniTuyaValve, valve_profile


def test_valve_entity_uses_core_valve_contract_and_only_explicit_profile():
    assert issubclass(OmniTuyaValve, ValveEntity)
    coordinator = type("Coordinator", (), {"dps_value": Mock(return_value=False)})()
    entity = OmniTuyaValve(
        coordinator,
        {"device_id": "garden-1", "name": "Garden valve", "domain": "valve"},
        "7",
        True,
        False,
    )
    assert entity.supported_features == (
        ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    )
    assert entity.unique_id == "omni_tuya_local_garden-1_valve"
    config = {
        "device_id": "garden-1",
        "domain": "valve",
        "tuya_functions": [{"code": "valve_switch", "dp_id": 7, "type": "Boolean"}],
    }
    assert valve_profile(config, {"7": False}) == ("7", True, False)
    assert valve_profile(config, {}) is None


def test_advanced_energy_profiles_use_core_classes_units_and_live_numeric_values():
    expected = {
        "reactive_power": (SensorDeviceClass.REACTIVE_POWER, UnitOfReactivePower.VOLT_AMPERE_REACTIVE),
        "apparent_power": (SensorDeviceClass.APPARENT_POWER, UnitOfApparentPower.VOLT_AMPERE),
        "frequency": (SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ),
        "power_factor": (SensorDeviceClass.POWER_FACTOR, None),
    }
    for code, profile in expected.items():
        assert _DPS_PROFILES[code][:2] == profile
        assert not _is_extended_profile_reported(code, {}, "42")
        assert not _is_extended_profile_reported(code, {"42": True}, "42")
        assert _is_extended_profile_reported(code, {"42": 0.5}, "42")


def test_core_valve_commands_remain_local_and_keep_stable_identity():
    coordinator = type(
        "Coordinator",
        (),
        {
            "async_set_status": AsyncMock(return_value=True),
            "dps_value": Mock(return_value=True),
        },
    )()
    config = {
        "device_id": "garden-1",
        "name": "Garden valve",
        "domain": "valve",
    }
    entity = OmniTuyaValve(coordinator, config, "7", True, False)
    async def exercise():
        await entity.async_open_valve()
        await entity.async_close_valve()

    asyncio.run(exercise())
    coordinator.async_set_status.assert_any_await("garden-1", True, 7)
    coordinator.async_set_status.assert_any_await("garden-1", False, 7)
