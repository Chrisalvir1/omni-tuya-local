import tests
import unittest

from custom_components.omni_tuya_local.util import (
    ha_to_tuya_brightness,
    tuya_to_ha_brightness,
    parse_physical_id,
    slugify,
)
from custom_components.omni_tuya_local.const import (
    TUYA_BRIGHTNESS_MAX,
    TUYA_BRIGHTNESS_MIN,
)


class TestUtil(unittest.TestCase):
    def test_brightness_conversions(self):
        # Minimum
        self.assertEqual(tuya_to_ha_brightness(TUYA_BRIGHTNESS_MIN), 0)
        self.assertEqual(ha_to_tuya_brightness(0), TUYA_BRIGHTNESS_MIN)

        # Maximum
        self.assertEqual(tuya_to_ha_brightness(TUYA_BRIGHTNESS_MAX), 255)
        self.assertEqual(ha_to_tuya_brightness(255), TUYA_BRIGHTNESS_MAX)

        # Mid-range
        mid_tuya = (TUYA_BRIGHTNESS_MAX + TUYA_BRIGHTNESS_MIN) // 2
        ha_val = tuya_to_ha_brightness(mid_tuya)
        self.assertTrue(120 <= ha_val <= 135)

    def test_parse_physical_id(self):
        self.assertEqual(parse_physical_id("device123"), ("device123", 1))
        self.assertEqual(parse_physical_id("device123_2"), ("device123", 2))
        self.assertEqual(parse_physical_id("device123_invalid"), ("device123_invalid", 1))

    def test_slugify(self):
        self.assertEqual(slugify("Living Room Lamp"), "living_room_lamp")
        self.assertEqual(slugify("Test-123_Device!"), "test_123_device")


if __name__ == "__main__":
    unittest.main()
