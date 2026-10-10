from __future__ import annotations

import tests  # initialize the Home Assistant test stubs before platform imports
import unittest
from unittest.mock import AsyncMock, Mock

from custom_components.omni_tuya_local.valve import OmniTuyaValve, valve_profile


class TestValveProfile(unittest.TestCase):
    def test_cloud_boolean_valve_requires_explicit_domain_and_live_dps(self):
        config = {
            "device_id": "water-1",
            "domain": "valve",
            "tuya_functions": [{"code": "valve_switch", "dp_id": 7, "type": "Boolean"}],
        }
        self.assertEqual(valve_profile(config, {"7": True}), ("7", True, False))
        self.assertIsNone(valve_profile(config, {}))
        self.assertIsNone(valve_profile({**config, "domain": "switch"}, {"7": True}))

    def test_manual_profile_uses_only_explicit_descriptor_and_values(self):
        config = {"domain": "valve", "dps_map": {"9": {
            "device_class": "valve", "open_value": "open", "closed_value": "closed",
        }}}
        self.assertEqual(valve_profile(config, {"9": "closed"}), ("9", "open", "closed"))
        self.assertIsNone(valve_profile(config, {"9": "unknown"}))
        self.assertIsNone(valve_profile({"domain": "valve", "dps_map": {"9": {}}}, {"9": False}))


class TestValveCommands(unittest.IsolatedAsyncioTestCase):
    async def test_open_and_close_use_configured_dps_without_cloud_control(self):
        coordinator = type("Coordinator", (), {
            "async_set_status": AsyncMock(return_value=True),
            "async_set_value": AsyncMock(return_value=True),
            "dps_value": Mock(return_value=True),
        })()
        config = {"device_id": "water-1", "name": "Water valve", "domain": "valve"}
        entity = OmniTuyaValve(coordinator, config, "7", True, False)
        await entity.async_open_valve()
        await entity.async_close_valve()
        coordinator.async_set_status.assert_any_await("water-1", True, 7)
        coordinator.async_set_status.assert_any_await("water-1", False, 7)
        self.assertTrue(entity.is_open)

    async def test_non_boolean_explicit_values_use_local_set_value(self):
        coordinator = type("Coordinator", (), {"async_set_value": AsyncMock(return_value=True)})()
        entity = OmniTuyaValve(coordinator, {"device_id": "water-1", "name": "Water valve"}, "9", "open", "closed")
        await entity.async_open_valve()
        await entity.async_close_valve()
        coordinator.async_set_value.assert_any_await("water-1", 9, "open")
        coordinator.async_set_value.assert_any_await("water-1", 9, "closed")
