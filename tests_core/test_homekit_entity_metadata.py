"""Verify Omni metadata through the real HomeKit Bridge accessory router."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import homeassistant.core
from homeassistant.core import State
from homeassistant.components.homekit import accessories
from custom_components.omni_tuya_local.switch import OmniTuyaSwitch
from custom_components.omni_tuya_local.sensor import OmniTuyaSensor


def test_outlet_is_routed_to_real_homekit_outlet_type():
    coord = SimpleNamespace(dps_value=Mock(return_value=True))
    entity = OmniTuyaSwitch(coord, {"device_id": "plug", "domain": "switch", "device_type": "outlet"})
    state = State("switch.sala", "on", {"device_class": entity.device_class})
    outlet = Mock()
    with patch.dict(accessories.TYPES, {"Outlet": outlet}):
        accessories.get_accessory(Mock(), Mock(), state, 10, {})
    outlet.assert_called_once()


def test_product_humidity_sensor_routes_as_homekit_humidity():
    coord = SimpleNamespace(data={"dps": {}}, dps_value=Mock(return_value=450))
    config = {"device_id": "sensor", "tuya_functions": [{"dp_id": 105, "code": "humidity_value", "type": "Integer", "values": '{"scale":1,"unit":"%"}'}]}
    entity = OmniTuyaSensor(coord, config, "105", {"code": "humidity_value"})
    state = State("sensor.humedad", str(entity.native_value), {"device_class": entity.device_class, "unit_of_measurement": entity.native_unit_of_measurement})
    humidity = Mock()
    with patch.dict(accessories.TYPES, {"HumiditySensor": humidity}):
        accessories.get_accessory(Mock(), Mock(), state, 11, {})
    humidity.assert_called_once()
    assert entity.native_value == 45
