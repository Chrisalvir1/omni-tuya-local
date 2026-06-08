from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
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
            if config.get("domain") != "alarm_control_panel":
                continue
            uid = f"{DOMAIN}_{config['device_id']}"
            if uid not in _known_unique_ids:
                _known_unique_ids.add(uid)
                entities.append(OmniTuyaAlarm(coordinator, config))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaAlarm(OmniTuyaEntity, AlarmControlPanelEntity):
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
    )

    @property
    def name(self) -> str:
        return self.config.get("name") or self.device_id

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        value = str(self.dps("1") or "").lower()
        if value in {"triggered", "alarm", "sos"}:
            return AlarmControlPanelState.TRIGGERED
        if value in {"home", "stay", "arm_home"}:
            return AlarmControlPanelState.ARMED_HOME
        if value in {"away", "armed", "arm", "arm_away", "true"}:
            return AlarmControlPanelState.ARMED_AWAY
        return AlarmControlPanelState.DISARMED

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self.coordinator.async_set_value(self.device_id, 1, "disarmed")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self.coordinator.async_set_value(self.device_id, 1, "home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self.coordinator.async_set_value(self.device_id, 1, "away")
