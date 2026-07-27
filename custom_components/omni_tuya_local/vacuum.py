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
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.BATTERY
    )

    @property
    def state(self) -> str | None:
        # Standard Tuya ``sd`` robots use DP 2 (power_go) for start/stop,
        # DP 3 for mode and DP 5 for status.  DP 1 is not a standard vacuum
        # control and caused this profile to remain idle in Home Assistant.
        status = self.dps("5")
        if isinstance(status, str):
            status = status.lower()
        if status in ("goto_charge",):
            return "returning"
        if status in ("charge", "charging", "charge_done", "dock", "docked"):
            return "docked"
        if status in ("cleaning", "smart_clean", "wall_clean", "spot_clean"):
            return "cleaning"

        mode = self.dps("3")
        if isinstance(mode, str) and mode.lower() == "chargego":
            return "returning"

        value = self.dps("2")
        if value is True or value == "on":
            return "cleaning"

        return "idle"

    @property
    def battery_level(self) -> int | None:
        val = self.dps("6")
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    async def async_start(self) -> None:
        await self.coordinator.async_set_status(self.device_id, True, 2)

    async def async_stop(self, **kwargs) -> None:
        await self.coordinator.async_set_status(self.device_id, False, 2)
        
    async def async_pause(self, **kwargs) -> None:
        await self.async_stop(**kwargs)

    async def async_return_to_base(self, **kwargs) -> None:
        # ``chargego`` is the documented command on the standard mode DP.
        # Do not spray values at unrelated product-specific DPS (101/104):
        # those can control a different feature on another Tuya robot.
        await self.coordinator.async_set_value(self.device_id, 3, "chargego")
