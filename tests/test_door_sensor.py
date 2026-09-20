import unittest
from unittest.mock import MagicMock

import tests  # initialize mocks

from custom_components.omni_tuya_local.models import (
    guess_domain,
    guess_device_type,
    sanitize_device_config,
)
from custom_components.omni_tuya_local.binary_sensor import OmniTuyaBinarySensor


class TestDoorSensor(unittest.TestCase):
    def test_door_sensor_detection(self):
        # Chinese product name WiFi门磁
        cfg_cn = {"name": "Door", "product_name": "WiFi门磁", "category": ""}
        self.assertEqual(guess_domain(cfg_cn), "binary_sensor")
        self.assertEqual(guess_device_type(cfg_cn), "door_sensor")

        # Spanish device name SENSOR PUERTA DE OFICINA
        cfg_es = {"name": "SENSOR PUERTA DE OFICINA", "product_name": "", "category": ""}
        self.assertEqual(guess_domain(cfg_es), "binary_sensor")
        self.assertEqual(guess_device_type(cfg_es), "door_sensor")

        # Mixed user setup
        cfg_user = {
            "name": "SENSOR PUERTA DE OFICINA",
            "product_name": "WiFi门磁",
            "category": "mcs",
        }
        self.assertEqual(guess_domain(cfg_user), "binary_sensor")
        self.assertEqual(guess_device_type(cfg_user), "door_sensor")

    def test_sanitize_existing_door_sensor_config(self):
        # A device erroneously saved as 'sensor' and 'generic'
        old_cfg = {
            "device_id": "bf3f78b02e35c47c84ozjm",
            "name": "SENSOR PUERTA DE OFICINA",
            "product_name": "WiFi门磁",
            "domain": "sensor",
            "device_type": "generic",
            "category": "",
        }
        sanitized, changed = sanitize_device_config(old_cfg)
        self.assertTrue(changed)
        self.assertEqual(sanitized["domain"], "binary_sensor")
        self.assertEqual(sanitized["device_type"], "door_sensor")
        self.assertEqual(sanitized["category"], "mcs")

    def test_binary_sensor_states(self):
        coordinator = MagicMock()
        coordinator.is_available.return_value = True

        cfg = {
            "device_id": "bf3f78b02e35c47c84ozjm",
            "name": "SENSOR PUERTA DE OFICINA",
            "product_name": "WiFi门磁",
            "domain": "binary_sensor",
            "device_type": "door_sensor",
        }

        # 1. When no DPS is received yet (sensor is asleep), do not invent a
        # closed state.  The UI must distinguish unknown from physically closed.
        coordinator.dps_value.return_value = None
        entity = OmniTuyaBinarySensor(coordinator, cfg)
        self.assertIsNone(entity.is_on)

        # 2. Open states
        for val in (True, "open", "OPEN", "opened", "1", "true"):
            coordinator.dps_value.return_value = val
            self.assertTrue(entity.is_on)

        # 3. Closed states
        for val in (False, "close", "CLOSE", "closed", "0", "false"):
            coordinator.dps_value.return_value = val
            self.assertFalse(entity.is_on)


if __name__ == "__main__":
    unittest.main()
