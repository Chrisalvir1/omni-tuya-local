from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tests

from custom_components.omni_tuya_local.camera import is_tuya_camera
from custom_components.omni_tuya_local.cloud import (
    TuyaCloudError,
    async_allocate_camera_stream,
)


class TestTuyaCamera(unittest.IsolatedAsyncioTestCase):
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
        self.assertFalse(is_tuya_camera({
            "category": "sp", "name": "Enchufe sala", "product_name": "Smart Plug"
        }))
        self.assertFalse(is_tuya_camera({"category": "cz", "name": "Video Plug"}))


if __name__ == "__main__":
    unittest.main()
