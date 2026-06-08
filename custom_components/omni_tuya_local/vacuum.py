from __future__ import annotations

from homeassistant.components.vacuum import StateVacuumEntity, VacuumEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    _known_unique_ids: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            if config.get("domain") != "vacuum":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaVacuum(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaVacuum(OmniTuyaEntity, StateVacuumEntity):
    _attr_supported_features = VacuumEntityFeature.START | VacuumEntityFeature.STOP | VacuumEntityFeature.RETURN_HOME

    @property
    def state(self) -> str | None:
        value = self.dps("1")
        if value is True or value == "on":
            return "cleaning"
        if value in ("charge", "charging", "dock", "docked"):
            return "docked"
        return "idle"

    async def async_start(self) -> None:
        await self.coordinator.async_set_status(self.device_id, True, 1)

    async def async_stop(self, **kwargs) -> None:
        await self.coordinator.async_set_status(self.device_id, False, 1)

    async def async_return_to_base(self, **kwargs) -> None:
        await self.coordinator.async_set_value(self.device_id, 1, "charge")
