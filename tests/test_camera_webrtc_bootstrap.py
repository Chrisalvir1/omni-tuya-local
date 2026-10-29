"""Tests do not need network access or real Tuya credentials."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock
import unittest

spec = importlib.util.spec_from_file_location("camera_webrtc", Path(__file__).parents[1] / "custom_components/omni_tuya_local/camera_webrtc.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BootstrapTests(unittest.TestCase):
    def test_two_way_bootstrap_is_ephemeral_and_uses_device_uid(self):
        client = Mock()
        config = {"supports_webrtc": True, "audio_attributes": {"call_mode": [1, 2], "hardware_capability": [1, 2]}, "auth": "secret", "moto_id": "moto", "p2p_config": {"ices": []}}
        client.cloudrequest.side_effect = [
            {"success": True, "result": config}, {"success": True, "result": {"uid": "user"}},
            {"success": True, "result": {"source_topic": {"ipc": "/av/u/from"}, "sink_topic": {"ipc": "/av/moto/moto/u/device"}}},
        ]
        result = module.allocate_webrtc(client, "device")
        assert result["audioAttributes"]["call_mode"] == [1, 2]
        assert client.cloudrequest.call_args.kwargs["post"]["uid"] == "user"
        assert len(client.cloudrequest.call_args.kwargs["post"]["link_id"]) == 8


    def test_api_failure_never_echoes_credentials(self):
        client = Mock()
        client.cloudrequest.return_value = {"success": False, "code": 123, "msg": "password=secret"}
        with self.assertRaises(module.CameraWebRtcError) as exc:
            module.allocate_webrtc(client, "device")
        assert "123" in str(exc.exception)
        assert "secret" not in str(exc.exception)


    def test_receive_only_device_does_not_allocate_mqtt_access(self):
        client = Mock()
        client.cloudrequest.return_value = {"success": True, "result": {"supports_webrtc": True, "audio_attributes": {"call_mode": [1], "hardware_capability": [1]}}}
        with self.assertRaises(module.CameraWebRtcError):
            module.allocate_webrtc(client, "device")
        assert client.cloudrequest.call_count == 1

if __name__ == "__main__":
    unittest.main()
