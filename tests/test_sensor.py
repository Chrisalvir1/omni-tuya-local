import tests
import unittest
from unittest.mock import MagicMock

from custom_components.omni_tuya_local.sensor import (
    OmniTuyaSensor,
    _DPS_PROFILES,
)


class TestSensor(unittest.TestCase):
    def setUp(self):
        self.coordinator = MagicMock()
        self.coordinator.data = {"dps": {}}

    def test_energy_sensor_profiles(self):
        # Power profile
        self.assertIn("19", _DPS_PROFILES)
        self.assertIn("cur_power", _DPS_PROFILES)

        # Voltage profile
        self.assertIn("20", _DPS_PROFILES)
        self.assertIn("cur_voltage", _DPS_PROFILES)

        # Current profile
        self.assertIn("18", _DPS_PROFILES)
        self.assertIn("cur_current", _DPS_PROFILES)

        # Energy profile
        self.assertIn("17", _DPS_PROFILES)
        self.assertIn("add_ele", _DPS_PROFILES)

    def test_power_sensor_value_scaling(self):
        config = {
            "device_id": "plug_1",
            "name": "Smart Plug",
            "domain": "switch",
            "device_type": "outlet",
        }
        sensor = OmniTuyaSensor(self.coordinator, config, "19", {"name": "Potencia"})
        
        # Power: 105 (tenth of watts) -> 10.5 W
        self.coordinator.dps_value.return_value = 105
        self.assertEqual(sensor.native_value, 10.5)

        # Power: 1500 (tenth of watts) -> 150.0 W
        self.coordinator.dps_value.return_value = 1500
        self.assertEqual(sensor.native_value, 150.0)

    def test_voltage_sensor_value_scaling(self):
        config = {
            "device_id": "plug_1",
            "name": "Smart Plug",
            "domain": "switch",
            "device_type": "outlet",
        }
        sensor = OmniTuyaSensor(self.coordinator, config, "20", {"name": "Voltaje"})

        # Voltage: 1205 (tenth of volts) -> 120.5 V
        self.coordinator.dps_value.return_value = 1205
        self.assertEqual(sensor.native_value, 120.5)

        # Voltage: 120 (already volts) -> 120.0 V
        self.coordinator.dps_value.return_value = 120
        self.assertEqual(sensor.native_value, 120.0)

    def test_current_sensor_value_scaling(self):
        config = {
            "device_id": "plug_1",
            "name": "Smart Plug",
            "domain": "switch",
            "device_type": "outlet",
        }
        sensor = OmniTuyaSensor(self.coordinator, config, "18", {"name": "Corriente"})

        # Current: 450 mA
        self.coordinator.dps_value.return_value = 450
        self.assertEqual(sensor.native_value, 450.0)

    def test_energy_sensor_value_scaling(self):
        config = {
            "device_id": "plug_1",
            "name": "Smart Plug",
            "domain": "switch",
            "device_type": "outlet",
        }
        sensor = OmniTuyaSensor(self.coordinator, config, "17", {"name": "Energía"})

        # Energy: 1500 (centikWh) -> 15.0 kWh
        self.coordinator.dps_value.return_value = 1500
        self.assertEqual(sensor.native_value, 15.0)

        # Energy: 25.5 (already kWh) -> 25.5 kWh
        self.coordinator.dps_value.return_value = 25.5
        self.assertEqual(sensor.native_value, 25.5)


    def test_is_energy_capable_device(self):
        from custom_components.omni_tuya_local.sensor import _is_energy_capable_device

        # Outlets and switches
        self.assertTrue(_is_energy_capable_device({"category": "cz"}, {}))
        self.assertTrue(_is_energy_capable_device({"category": "pc"}, {}))
        self.assertTrue(_is_energy_capable_device({"device_type": "outlet"}, {}))
        self.assertTrue(_is_energy_capable_device({"product_name": "Smart Plug Duo"}, {}))
        self.assertTrue(_is_energy_capable_device({}, {"19": 100}))
        self.assertTrue(_is_energy_capable_device({}, {19: 100}))

        # Non-energy devices
        self.assertFalse(_is_energy_capable_device({"domain": "light", "device_type": "light"}, {}))

    def test_switch_energy_attributes_with_zero_values(self):
        from custom_components.omni_tuya_local.switch import OmniTuyaSwitch
        
        config = {
            "device_id": "plug_1",
            "name": "Smart Plug",
            "domain": "switch",
            "device_type": "outlet",
        }
        sw = OmniTuyaSwitch(self.coordinator, config, "1")
        
        # When device reports 0 watts (DPS 19 = 0)
        self.coordinator.dps_value.side_effect = lambda dev_id, dps_id: 0 if str(dps_id) in ("19", "20", "18", "17") else None
        self.assertEqual(sw.current_power_w, 0.0)
        attrs = sw.extra_state_attributes
        self.assertEqual(attrs.get("current_power_w"), 0.0)
        self.assertEqual(attrs.get("voltage"), 0.0)
        self.assertEqual(attrs.get("current_a"), 0.0)
    def test_vacuum_battery_and_attributes(self):
        from custom_components.omni_tuya_local.vacuum import OmniTuyaVacuum

        config = {
            "device_id": "vacuum_1",
            "name": "Robot Vacuum",
            "domain": "vacuum",
            "device_type": "robot_vacuum",
        }
        vac = OmniTuyaVacuum(self.coordinator, config)

        self.coordinator.dps_value.side_effect = lambda dev_id, dps_id: 85 if str(dps_id) == "6" else (250 if str(dps_id) == "19" else None)
        self.assertEqual(vac.battery_level, 85)
        self.assertEqual(vac.current_power_w, 25.0)
        attrs = vac.extra_state_attributes
        self.assertEqual(attrs.get("battery_level"), 85)
        self.assertEqual(attrs.get("current_power_w"), 25.0)


if __name__ == "__main__":
    unittest.main()
