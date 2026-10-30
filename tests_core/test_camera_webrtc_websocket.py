"""Exercise the camera WebRTC command through Home Assistant's real decorators."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import asyncio
import pytest
from homeassistant.exceptions import Unauthorized

from custom_components.omni_tuya_local import (
    OmniTuyaLocalCoordinator,
    _async_register_camera_webrtc_websocket,
)


@pytest.mark.asyncio
async def test_real_websocket_dispatch_allocates_webrtc_and_checks_admin():
    hass = MagicMock()
    hass.data = {}
    tasks = []

    def create_task(coro, *args, **kwargs):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    hass.async_create_background_task.side_effect = create_task
    connection = MagicMock(
        spec=["user", "send_result", "send_error", "async_handle_exception"]
    )
    connection.user = SimpleNamespace(is_admin=True)
    msg = {
        "id": 8,
        "type": "omni_tuya_local/camera_webrtc",
        "entity_id": "camera.feeder",
    }
    entity = SimpleNamespace(
        domain="camera",
        platform="omni_tuya_local",
        unique_id="omni_tuya_local_device123_camera",
    )
    registry = MagicMock()
    registry.async_get.return_value = entity
    hass.data["entity_registry"] = registry
    coordinator = object.__new__(OmniTuyaLocalCoordinator)
    coordinator.store = SimpleNamespace(cloud_config={"region": "eu"})
    coordinator.get_device_config = MagicMock(
        return_value={"cloud_id": "cloud-device"}
    )
    hass.data["omni_tuya_local"] = {"entry": coordinator}

    with (
        patch(
            "custom_components.omni_tuya_local.er.async_get",
            return_value=registry,
        ),
        patch(
            "custom_components.omni_tuya_local.async_allocate_webrtc",
            new_callable=AsyncMock,
            return_value={"deviceId": "cloud-device", "auth": "transient"},
        ) as allocate,
        patch(
            "custom_components.omni_tuya_local.websocket_api.async_register_command"
        ) as register,
    ):
        _async_register_camera_webrtc_websocket(hass)
        handler = register.call_args.args[1]
        handler(hass, connection, msg)
        await asyncio.gather(*tasks)
        allocate.assert_awaited_once_with(
            hass, {"region": "eu"}, "cloud-device"
        )
        connection.send_result.assert_called_once_with(
            8, {"deviceId": "cloud-device", "auth": "transient"}
        )
        connection.async_handle_exception.assert_not_called()

        connection.user = SimpleNamespace(is_admin=False)
        with pytest.raises(Unauthorized):
            handler(hass, connection, msg)
        assert allocate.await_count == 1
