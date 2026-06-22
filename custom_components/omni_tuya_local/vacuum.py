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
    _attr_supported_features = VacuumEntityFeature.START | VacuumEntityFeature.STOP | VacuumEntityFeature.RETURN_HOME | VacuumEntityFeature.PAUSE

    @property
    def state(self) -> str | None:
        value = self.dps("1")
        if value is True or value == "on":
            return "cleaning"
            
        # Check DP 3 for chargego state or DP 5 for goto_charge
        mode = self.dps("3")
        if isinstance(mode, str):
            mode = mode.lower()
        if mode in ("chargego", "charge", "charging", "dock", "docked"):
            return "docked"
            
        status = self.dps("5")
        if isinstance(status, str):
            status = status.lower()
        if status in ("goto_charge", "charge", "charging", "dock", "docked"):
            return "docked"

        if isinstance(value, str):
            value = value.lower()
        if value in ("charge", "charging", "dock", "docked"):
            return "docked"
        return "idle"

    async def async_start(self) -> None:
        await self.coordinator.async_set_status(self.device_id, True, 1)

    async def async_stop(self, **kwargs) -> None:
        await self.coordinator.async_set_status(self.device_id, False, 1)
        
    async def async_pause(self, **kwargs) -> None:
        await self.async_stop(**kwargs)

    async def async_return_to_base(self, **kwargs) -> None:
        # Enviar comandos a los DPs conocidos de dock sin depender de raw_dps
        # Evitamos enviar a DP 1 (que suele ser el interruptor on/off) para no
        # sobreescribir el comando de dock con un "stop/inactivo".
        commands = [
            (101, "Charge"),
            (104, "Charge"),
            (3, "chargego"),
            (5, "goto_charge")
        ]
        
        import asyncio
        tasks = [
            self.coordinator.async_set_value(self.device_id, dps_id, val)
            for dps_id, val in commands
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
