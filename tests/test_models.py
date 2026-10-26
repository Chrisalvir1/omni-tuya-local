import tests
import unittest

from custom_components.omni_tuya_local.models import (
    guess_domain,
    guess_device_type,
    TuyaDeviceConfig,
    normalize_device,
    sanitize_device_config,
)


class TestModels(unittest.TestCase):
    def test_guess_domain_by_category(self):
        self.assertEqual(guess_domain({"category": "dj"}), "light")
        self.assertEqual(guess_domain({"category": "cz"}), "switch")
        self.assertEqual(guess_domain({"category": "kt"}), "climate")
        self.assertEqual(guess_domain({"category": "cl"}), "cover")
        self.assertEqual(guess_domain({"category": "ms"}), "lock")
        self.assertEqual(guess_domain({"category": "pir"}), "binary_sensor")
        self.assertEqual(guess_domain({"category": "wsdcg"}), "sensor")
        self.assertEqual(guess_domain({"category": "sd"}), "vacuum")
        self.assertEqual(guess_domain({"category": "ywj"}), "alarm_control_panel")
        self.assertEqual(guess_domain({"category": "jsq"}), "humidifier")

    def test_guess_domain_by_name_and_product(self):
        self.assertEqual(guess_domain({"name": "Ceiling Light"}), "light")
        self.assertEqual(guess_domain({"name": "Front Door Lock"}), "lock")
        self.assertEqual(guess_domain({"product_name": "Smart AC Thermostat"}), "climate")
        self.assertEqual(guess_domain({"name": "Living Room Curtains"}), "cover")
        self.assertEqual(guess_domain({"product_name": "Robot Vacuum Cleaner"}), "vacuum")
        self.assertEqual(guess_domain({"name": "Dual Smart Plug Duo"}), "switch")
        self.assertEqual(guess_domain({"name": "ROBOTINA", "model": "A1-ROPVACNIC"}), "vacuum")
        self.assertEqual(guess_domain({"name": "ROBOTINA", "product_id": "A1-ROPVACNIC"}), "vacuum")
        self.assertEqual(guess_domain({"name": "ROBOTINA", "raw": {"model": "A1-ROPVACNIC"}}), "vacuum")

    def test_guess_device_type(self):
        self.assertEqual(guess_device_type({"category": "cz"}), "outlet")
        self.assertEqual(guess_device_type({"category": "pc"}), "power_strip")
        self.assertEqual(guess_device_type({"category": "kt"}), "air_conditioner")
        self.assertEqual(guess_device_type({"category": "cwwsq"}), "pet_feeder")
        self.assertEqual(guess_device_type({"product_name": "Smart Coffee Maker"}), "coffee_maker")
        self.assertEqual(guess_device_type({"name": "Electric Kettle"}), "kettle")
        self.assertEqual(guess_device_type({"product_name": "Air Purifier Pro"}), "air_purifier")
        self.assertEqual(guess_device_type({"name": "ROBOTINA", "model": "A1-ROPVACNIC"}), "robot_vacuum")
        self.assertEqual(guess_device_type({"name": "ROBOTINA", "raw": {"model": "A1-ROPVACNIC"}}), "robot_vacuum")

    def test_sanitize_robotina_model_overrides_cloud_generic_classification(self):
        data, changed = sanitize_device_config({
            "name": "ROBOTINA",
            "product_id": "A1-ROPVACNIC",
            "domain": "switch",
            "device_type": "outlet",
        })
        self.assertTrue(changed)
        self.assertEqual(data["domain"], "vacuum")
        self.assertEqual(data["device_type"], "robot_vacuum")

    def test_tuya_device_config(self):
        raw = {
            "device_id": "test_id_123",
            "name": "Kitchen Outlet",
            "local_key": "secret_key_1234",
            "host": "192.168.1.50",
            "version": "3.3",
            "category": "cz",
        }
        config = TuyaDeviceConfig.from_dict(raw)
        self.assertEqual(config.device_id, "test_id_123")
        self.assertEqual(config.name, "Kitchen Outlet")
        self.assertEqual(config.domain, "switch")
        self.assertEqual(config.device_type, "outlet")
        self.assertTrue(config.has_host)
        self.assertEqual(config.effective_host, "192.168.1.50")
        self.assertEqual(config.local_key_masked, "***********1234")

        as_dict = config.as_dict()
        self.assertEqual(as_dict["device_id"], "test_id_123")
        self.assertEqual(as_dict["lan_device_id"], "test_id_123")
        self.assertEqual(as_dict["domain"], "switch")

    def test_reset_device_uses_current_lan_id_while_preserving_ha_id(self):
        from unittest.mock import MagicMock, patch
        from custom_components.omni_tuya_local.device import OmniTuyaDevice

        config = {
            "device_id": "stable-ha-id",
            "lan_device_id": "current-tuya-id",
            "name": "Renamed plug",
            "local_key": "current-key",
            "host": "192.168.1.50",
        }
        device = OmniTuyaDevice(MagicMock(), config)
        with patch("tinytuya.Device") as tuya_device:
            device._build_tuya()
        self.assertEqual(device.device_id, "stable-ha-id")
        self.assertEqual(tuya_device.call_args.kwargs["dev_id"], "current-tuya-id")

    def test_normalize_device(self):
        raw = {
            "id": "dev_999",
            "name": "Bedroom Lamp",
            "key": "key999",
            "ip": "192.168.1.10",
            "category": "dj",
        }
        normalized = normalize_device(raw)
        self.assertEqual(normalized["device_id"], "dev_999")
        self.assertEqual(normalized["local_key"], "key999")
        self.assertEqual(normalized["host"], "192.168.1.10")
        self.assertEqual(normalized["domain"], "light")

    def test_sleep_device_detection(self):
        from custom_components.omni_tuya_local.device import OmniTuyaDevice
        from unittest.mock import MagicMock
        hass = MagicMock()
        door_cfg = {
            "device_id": "door_123",
            "name": "Puerta",
            "category": "mcs",
            "device_type": "door_sensor",
            "host": "192.168.1.50",
            "local_key": "key123",
        }
        dev = OmniTuyaDevice(hass, door_cfg)
        self.assertTrue(dev.is_sleep_device)
        self.assertTrue(dev.available)


if __name__ == "__main__":
    unittest.main()
