import tests
import unittest
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from custom_components.omni_tuya_local.cloud import (
    normalize_mac,
    find_cloud_device_by_mac,
    async_fetch_cloud_devices,
)


class TestCloud(unittest.IsolatedAsyncioTestCase):
    def test_normalize_mac(self):
        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF"), "aabbccddeeff")
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "aabbccddeeff")
        self.assertEqual(normalize_mac("aabb.ccdd.eeff"), "aabbccddeeff")
        self.assertEqual(normalize_mac("AABBCCDDEEFF"), "aabbccddeeff")
        self.assertEqual(normalize_mac("invalid"), "")
        self.assertEqual(normalize_mac(None), "")

    def test_find_cloud_device_by_mac(self):
        devices = [
            {"id": "dev1", "mac": "aa:bb:cc:dd:ee:01", "name": "Device 1"},
            {"id": "dev2", "raw": {"mac_address": "AA-BB-CC-DD-EE-02"}, "name": "Device 2"},
            {"id": "dev3", "raw": {"mac": "aabbccddee03"}, "name": "Device 3"},
        ]
        self.assertEqual(find_cloud_device_by_mac(devices, "AA:BB:CC:DD:EE:01")["id"], "dev1")
        self.assertEqual(find_cloud_device_by_mac(devices, "aabb.ccdd.ee02")["id"], "dev2")
        self.assertEqual(find_cloud_device_by_mac(devices, "AA:BB:CC:DD:EE:03")["id"], "dev3")
        self.assertIsNone(find_cloud_device_by_mac(devices, "00:11:22:33:44:55"))

    async def test_fetch_cloud_devices_with_tuya_openapi_local_key(self):
        """Test that devices returned from Tuya OpenAPI with 'local_key' preserve the key."""
        hass = MagicMock()
        async def fake_executor_job(func, *args, **kwargs):
            return func(*args, **kwargs)
        hass.async_add_executor_job = fake_executor_job

        mock_cloud_instance = MagicMock()
        # Simulate Tuya OpenAPI returning local_key for a user's devices
        mock_cloud_instance.cloudrequest.return_value = {
            "result": [
                {
                    "id": "dev_tuya_01",
                    "name": "Smart Switch 1",
                    "local_key": "tuya_secret_key_1",
                    "category": "cz",
                    "product_name": "Smart Plug",
                    "ip": "192.168.1.101",
                    "mac": "AA:BB:CC:11:22:33",
                }
            ],
            "success": True,
        }
        mock_cloud_instance.getfunctions.return_value = {"result": []}

        with patch("tinytuya.Cloud", return_value=mock_cloud_instance):
            devices = await async_fetch_cloud_devices(
                hass=hass,
                api_key="test_key",
                api_secret="test_secret",
                api_region="eu",
                device_id="eu1621898281305Wo1vo",
            )

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_id"], "dev_tuya_01")
        self.assertEqual(devices[0]["local_key"], "tuya_secret_key_1")
        self.assertEqual(devices[0]["domain"], "switch")
        self.assertEqual(devices[0]["host"], "192.168.1.101")

    async def test_fetch_cloud_devices_with_multiple_uids(self):
        """Test comma-separated UIDs as used in the UI."""
        hass = MagicMock()
        async def fake_executor_job(func, *args, **kwargs):
            return func(*args, **kwargs)
        hass.async_add_executor_job = fake_executor_job

        mock_cloud_instance = MagicMock()
        def fake_cloudrequest(path):
            if "eu1621898281305Wo1vo" in path:
                return {
                    "result": [
                        {
                            "id": "dev_uid1",
                            "name": "Device UID 1",
                            "local_key": "key_uid_1",
                            "category": "cz",
                        }
                    ]
                }
            elif "eu16078311586760h2mt" in path:
                return {
                    "result": [
                        {
                            "id": "dev_uid2",
                            "name": "Device UID 2",
                            "local_key": "key_uid_2",
                            "category": "dj",
                        }
                    ]
                }
            return {"result": []}

        mock_cloud_instance.cloudrequest.side_effect = fake_cloudrequest
        mock_cloud_instance.getfunctions.return_value = {"result": []}

        with patch("tinytuya.Cloud", return_value=mock_cloud_instance):
            devices = await async_fetch_cloud_devices(
                hass=hass,
                api_key="test_key",
                api_secret="test_secret",
                api_region="eu",
                device_id="eu1621898281305Wo1vo, eu16078311586760h2mt",
            )

        self.assertEqual(len(devices), 2)
        dev_ids = {d["device_id"] for d in devices}
        self.assertEqual(dev_ids, {"dev_uid1", "dev_uid2"})
        for d in devices:
            self.assertTrue(bool(d["local_key"]))

    async def test_fetch_cloud_devices_fallback_detail_for_missing_key(self):
        """Test fallback to GET /v1.0/devices/{id} when local_key is omitted in list."""
        hass = MagicMock()
        async def fake_executor_job(func, *args, **kwargs):
            return func(*args, **kwargs)
        hass.async_add_executor_job = fake_executor_job

        mock_cloud_instance = MagicMock()
        # Device list without local_key
        mock_cloud_instance.cloudrequest.side_effect = [
            # 1. users/{uid}/devices
            {"result": [{"id": "dev_missing_key", "name": "Device Without Key", "category": "cz"}]},
            # 2. devices/{dev_id} fallback lookup
            {"result": {"id": "dev_missing_key", "local_key": "recovered_key_123"}},
        ]
        mock_cloud_instance.getfunctions.return_value = {"result": []}

        with patch("tinytuya.Cloud", return_value=mock_cloud_instance):
            devices = await async_fetch_cloud_devices(
                hass=hass,
                api_key="test_key",
                api_secret="test_secret",
                api_region="eu",
                device_id="eu1621898281305Wo1vo",
            )

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_id"], "dev_missing_key")
        self.assertEqual(devices[0]["local_key"], "recovered_key_123")


if __name__ == "__main__":
    unittest.main()
