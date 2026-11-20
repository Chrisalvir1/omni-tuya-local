import tests
import unittest
from types import SimpleNamespace

from custom_components.omni_tuya_local.pet_feeder import (
    function_id,
    pet_feeder_feed,
    pet_feeder_clean_hopper,
)


from custom_components.omni_tuya_local.switch import _switch_dps


class TestPetFeeder(unittest.TestCase):
    def test_function_id(self):
        self.assertEqual(function_id({"dp_id": 3}), "3")
        self.assertEqual(function_id({"dpId": "4"}), "4")
        self.assertEqual(function_id({"id": 201}), "201")
        self.assertIsNone(function_id({"other": 1}))

    def test_pet_feeder_feed_from_config(self):
        config = {
            "pet_feeder_feed_dp": "201",
            "pet_feeder_feed_kind": "value",
        }
        res = pet_feeder_feed(config, {})
        self.assertEqual(res, ("201", "value"))

    def test_pet_feeder_feed_from_functions(self):
        config = {
            "tuya_functions": [
                {"dp_id": 3, "code": "manual_feed"},
            ]
        }
        res = pet_feeder_feed(config, {})
        self.assertEqual(res, ("3", "value"))

        config_quick = {
            "tuya_functions": [
                {"dp_id": 2, "code": "quick_feed"},
            ]
        }
        res_quick = pet_feeder_feed(config_quick, {})
        self.assertEqual(res_quick, ("2", "bool"))

    def test_pet_feeder_feed_fallback_raw_dps(self):
        res = pet_feeder_feed({}, {"3": 5})
        self.assertEqual(res, ("3", "value"))

        res_201 = pet_feeder_feed({}, {"201": 1})
        self.assertEqual(res_201, ("201", "value"))

        res_bool = pet_feeder_feed({}, {"2": True})
        self.assertEqual(res_bool, ("2", "bool"))

    def test_switch_restores_persisted_feed_channel_before_polling(self):
        config = {
            "device_id": "feeder",
            "device_type": "pet_feeder",
            "discovered_dps": {"201": {"kind": "number"}},
        }
        coordinator = SimpleNamespace(data=None, devices={})
        self.assertEqual(_switch_dps(config, coordinator), [("201", "Alimentar ahora")])
        self.assertEqual(_switch_dps({**config, "discovered_dps": {}}, coordinator), [])
        self.assertIsNone(pet_feeder_feed(config, {"201": False}))

    def test_pet_feeder_clean_hopper(self):
        config = {
            "pet_feeder_clean_hopper_dp": "105",
            "pet_feeder_clean_hopper_value": True,
        }
        res = pet_feeder_clean_hopper(config)
        self.assertEqual(res, ("105", True))

        self.assertIsNone(pet_feeder_clean_hopper({}))


if __name__ == "__main__":
    unittest.main()
