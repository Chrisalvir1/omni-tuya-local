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


if __name__ == "__main__":
    unittest.main()
