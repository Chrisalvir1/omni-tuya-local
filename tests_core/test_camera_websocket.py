"""Exercise Omni with the real Home Assistant WebSocket decorators."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.core
import pytest
from homeassistant.exceptions import Unauthorized

from custom_components.omni_tuya_local import _async_register_camera_stream_websocket


@pytest.mark.asyncio
async def test_real_websocket_dispatch_allocates_stream_and_checks_admin():
    hass = MagicMock()
    hass.data = {}
    tasks = []

    def create_task(coro, *args, **kwargs):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    hass.async_create_background_task.side_effect = create_task
    connection = MagicMock(spec=["user", "send_result", "send_error", "async_handle_exception"])
    connection.user = SimpleNamespace(is_admin=True)
    msg = {"id": 7, "type": "omni_tuya_local/camera_stream", "entity_id": "camera.feeder"}
    with patch("custom_components.omni_tuya_local.websocket_api.async_register_command") as register, patch(
        "custom_components.omni_tuya_local._async_fresh_camera_url", new_callable=AsyncMock,
        return_value="rtsps://example.invalid/new-session",
    ) as allocate:
        _async_register_camera_stream_websocket(hass)
        handler = register.call_args.args[1]
        handler(hass, connection, msg)
        await asyncio.gather(*tasks)
        allocate.assert_awaited_once_with(hass, "camera.feeder")
        connection.send_result.assert_called_once_with(7, {"url": "rtsps://example.invalid/new-session"})
        connection.async_handle_exception.assert_not_called()
        allocate.reset_mock()
        connection.user = SimpleNamespace(is_admin=False)
        with pytest.raises(Unauthorized):
            handler(hass, connection, msg)
        allocate.assert_not_awaited()
