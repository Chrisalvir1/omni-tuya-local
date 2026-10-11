"""Tuya IPC camera streams."""

from __future__ import annotations

import logging

from homeassistant.components import ffmpeg
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .cloud import TuyaCloudError, async_allocate_camera_stream
from .const import CONF_API_KEY, CONF_API_SECRET, CONF_REGION, DEFAULT_REGION, DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity

_LOGGER = logging.getLogger(__name__)


def is_tuya_camera(config: dict) -> bool:
    """Recognize Tuya IPC products without treating ordinary plugs as cameras."""
    category = str(config.get("category") or "").lower()
    if category == "dghsxj":
        return True
    if category not in ("sp", "cwwsq"):
        return False
    raw = config.get("raw") if isinstance(config.get("raw"), dict) else {}
    description = " ".join(
        str(source.get(key) or "")
        for source in (config, raw)
        for key in ("name", "product_name", "device_type", "category_name")
    ).lower()
    return any(
        marker in description
        for marker in ("camera", "cámara", "camara", "video", "ipc")
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Add a camera entity for each supported Tuya IPC device."""
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    cameras = [
        OmniTuyaCamera(coordinator, config)
        for config in coordinator.store.all().values()
        if is_tuya_camera(config)
    ]
    if cameras:
        async_add_entities(cameras)


class OmniTuyaCamera(OmniTuyaEntity, Camera):
    """Camera entity backed by a fresh Tuya RTSP stream allocation."""

    _attr_name = None
    _attr_brand = "Tuya"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict) -> None:
        super().__init__(coordinator, config, "camera")
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_camera"
        self._attr_model = config.get("product_name") or "Tuya IPC"
        Camera.__init__(self)

    @property
    def available(self) -> bool:
        """Use cloud readiness for video; LAN DPS polling does not gate RTSP."""
        cloud_config = getattr(self.coordinator.store, "cloud_config", {}) or {}
        device_config = self.coordinator.get_device_config(self.device_id) or self.config
        return bool(
            cloud_config.get(CONF_API_KEY)
            and cloud_config.get(CONF_API_SECRET)
            and (device_config.get("cloud_id") or self.device_id)
        )

    async def stream_source(self) -> str | None:
        """Allocate a new signed Tuya RTSP URL for each stream request."""
        cloud_config = getattr(self.coordinator.store, "cloud_config", {}) or {}
        config = self.coordinator.get_device_config(self.device_id) or self.config
        try:
            return await async_allocate_camera_stream(
                self.hass,
                cloud_config.get(CONF_API_KEY, ""),
                cloud_config.get(CONF_API_SECRET, ""),
                cloud_config.get(CONF_REGION, DEFAULT_REGION),
                config.get("cloud_id") or self.device_id,
            )
        except TuyaCloudError as err:
            _LOGGER.warning("Could not allocate Tuya camera stream for %s: %s", self.device_id, err)
            return None

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return a still image using a newly allocated RTSP URL."""
        source = await self.stream_source()
        if not source:
            return None
        return await ffmpeg.async_get_image(
            self.hass,
            source,
            width=width,
            height=height,
        )
