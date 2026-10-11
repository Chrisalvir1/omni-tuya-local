from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tests

from custom_components.omni_tuya_local.camera import OmniTuyaCamera, is_tuya_camera
from custom_components.omni_tuya_local import _async_fresh_camera_url
from custom_components.omni_tuya_local.const import DOMAIN
from custom_components.omni_tuya_local.coordinator import OmniTuyaLocalCoordinator
from custom_components.omni_tuya_local.cloud import (
    TuyaCloudError,
    async_allocate_camera_stream,
)


class TestTuyaCamera(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_url_requires_registered_omni_camera_entity(self):
        hass = MagicMock()
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(
            domain="camera", platform="tuya", unique_id="not-omni"
        )
        with patch("custom_components.omni_tuya_local.er.async_get", return_value=registry):
            with self.assertRaisesRegex(ValueError, "not found"):
                await _async_fresh_camera_url(hass, "camera.feeder")

    async def test_fresh_url_uses_current_cloud_credentials_and_device_id(self):
        hass = MagicMock()
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(
            domain="camera",
            platform=DOMAIN,
            unique_id=f"{DOMAIN}_device-1_camera",
        )
        coordinator = object.__new__(OmniTuyaLocalCoordinator)
        coordinator.store = SimpleNamespace(cloud_config={
            "api_key": "key", "api_secret": "secret", "region": "us"
        })
        coordinator.get_device_config = MagicMock(return_value={
            "device_id": "device-1", "cloud_id": "cloud-device-1"
        })
        hass.data = {DOMAIN: {"entry": coordinator}}
        with patch("custom_components.omni_tuya_local.er.async_get", return_value=registry), patch(
            "custom_components.omni_tuya_local.async_allocate_camera_stream",
            return_value="rtsps://tuya.invalid/session-token",
        ) as allocate:
            url = await _async_fresh_camera_url(hass, "camera.feeder")

        self.assertEqual(url, "rtsps://tuya.invalid/session-token")
        allocate.assert_awaited_once_with(
            hass, "key", "secret", "us", "cloud-device-1"
        )

    async def test_allocates_fresh_rtsp_url_using_cloud_api(self):
        hass = MagicMock()

        async def executor(func, *args):
            return func(*args)

        hass.async_add_executor_job = executor
        cloud = MagicMock()
        cloud.cloudrequest.return_value = {
            "success": True,
            "result": {"url": "rtsps://example.invalid/live?token=secret"},
        }
        with patch("tinytuya.Cloud", return_value=cloud) as cloud_factory:
            url = await async_allocate_camera_stream(
                hass, "api-key", "api-secret", "us", "camera-1"
            )

        self.assertEqual(url, "rtsps://example.invalid/live?token=secret")
        cloud_factory.assert_called_once_with(
            apiRegion="us",
            apiKey="api-key",
            apiSecret="api-secret",
            apiDeviceID="camera-1",
        )
        cloud.cloudrequest.assert_called_once_with(
            "/v1.0/devices/camera-1/stream/actions/allocate",
            action="POST",
            post={"type": "rtsp"},
        )

    async def test_rejects_failed_or_non_rtsp_stream_response(self):
        hass = MagicMock()

        async def executor(func, *args):
            return func(*args)

        hass.async_add_executor_job = executor
        cloud = MagicMock()
        cloud.cloudrequest.return_value = {
            "success": False,
            "result": {"url": "rtsps://secret.invalid/token"},
            "code": 28841107,
        }
        with patch("tinytuya.Cloud", return_value=cloud):
            with self.assertRaisesRegex(TuyaCloudError, "28841107") as caught:
                await async_allocate_camera_stream(
                    hass, "api-key", "api-secret", "us", "camera-1"
                )
        self.assertNotIn("secret.invalid", str(caught.exception))

    async def test_requires_cloud_credentials(self):
        with self.assertRaises(TuyaCloudError):
            await async_allocate_camera_stream(
                MagicMock(), "", "", "us", "camera-1"
            )

    def test_detects_video_feeder_and_camera_without_matching_plugs(self):
        self.assertTrue(is_tuya_camera({
            "category": "sp",
            "name": "COMEDERO MICHI",
            "product_name": "Smart Video Feeder",
        }))
        self.assertTrue(is_tuya_camera({"category": "dghsxj", "name": "IPC"}))
        self.assertTrue(is_tuya_camera({
            "category": "cwwsq",
            "name": "COMEDERO MICHI",
            "product_name": "Smart Video Feeder",
        }))
        self.assertFalse(is_tuya_camera({
            "category": "cwwsq", "name": "COMEDERO MICHI", "product_name": "Pet Feeder"
        }))
        self.assertFalse(is_tuya_camera({
            "category": "sp", "name": "Enchufe sala", "product_name": "Smart Plug"
        }))
        self.assertFalse(is_tuya_camera({"category": "cz", "name": "Video Plug"}))

    def test_camera_availability_uses_cloud_credentials_not_lan_poll(self):
        camera = object.__new__(OmniTuyaCamera)
        camera.coordinator = SimpleNamespace(
            store=SimpleNamespace(cloud_config={"api_key": "key", "api_secret": "secret"}),
            get_device_config=lambda device_id: {"cloud_id": "cloud-device"},
            is_available=lambda device_id: False,
        )
        camera.device_id = "local-device"
        camera.config = {"device_id": "local-device"}

        self.assertTrue(camera.available)

        camera.coordinator.store.cloud_config["api_secret"] = ""
        self.assertFalse(camera.available)


if __name__ == "__main__":
    unittest.main()
