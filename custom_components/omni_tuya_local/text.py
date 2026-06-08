from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya text entities from a config entry."""
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for device_id, config in coordinator.store.all().items():
            uid = f"{DOMAIN}_{device_id}_ip_address"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(TuyaIpTextEntity(coordinator, device_id, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class TuyaIpTextEntity(TextEntity):
    """Text entity to display and edit the device's IP address directly from the device page."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, device_id: str, config: dict[str, Any]) -> None:
        """Initialize the text entity."""
        self.coordinator = coordinator
        self.device_id = device_id
        
        # Entity attributes
        self._attr_unique_id = f"{DOMAIN}_{device_id}_ip_address"
        self._attr_name = "Dirección IP"

        device_name = config.get("name") or device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="Tuya",
        )

    @property
    def native_value(self) -> str | None:
        """Return the value of the text entity (the IP address)."""
        config = self.coordinator.get_device_config(self.device_id) or {}
        return config.get("host") or config.get("ip") or ""

    async def async_set_value(self, value: str) -> None:
        """Update the IP address."""
        value = value.strip()
        if value and not self._is_valid_ip(value):
            _LOGGER.error("Invalid IP address provided: %s", value)
            return

        # Fetch current config from store
        config = self.coordinator.get_device_config(self.device_id) or {}
        updated = dict(config)
        updated["host"] = value
        updated["ip"] = value

        # Save to store
        await self.coordinator.store.add(updated)
        
        # Reload devices to apply new IP
        await self.coordinator.async_reload_devices()
        
        # Inform HA of state change
        self.async_write_ha_state()

    def _is_valid_ip(self, ip: str) -> bool:
        """Basic IP address format check."""
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, ip):
            return False
        return all(0 <= int(part) <= 255 for part in ip.split("."))
