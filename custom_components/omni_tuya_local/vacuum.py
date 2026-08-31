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


def _first_valid_dps(entity: OmniTuyaEntity, *keys: str | int) -> Any:
    for k in keys:
        val = entity.dps(k)
        if val is not None:
            return val
    return None


class OmniTuyaVacuum(OmniTuyaEntity, StateVacuumEntity):
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.PAUSE
    )

    @property
    def current_power_w(self) -> float | None:
        """Potencia de consumo de la base/estación si está disponible (W)."""
        val = _first_valid_dps(self, "19", "cur_power", "power")
        if val is not None:
            try:
                return round(float(val) / 10.0, 1)
            except (TypeError, ValueError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes

        # Telemetría de energía de estación/base (Eve Energy / Home+)
        power_val = _first_valid_dps(self, "19", "cur_power", "power")
        if power_val is not None:
            try:
                p = round(float(power_val) / 10.0, 1)
                attrs["current_power_w"] = p
                attrs["power"] = p
            except (TypeError, ValueError):
                pass

        voltage_val = _first_valid_dps(self, "20", "cur_voltage", "voltage")
        if voltage_val is not None:
            try:
                v = float(voltage_val)
                attrs["voltage"] = round(v / 10.0, 1) if v > 500 else round(v, 1)
            except (TypeError, ValueError):
                pass

        current_val = _first_valid_dps(self, "18", "cur_current", "current")
        if current_val is not None:
            try:
                c = float(current_val)
                attrs["current_a"] = round(c / 1000.0, 3)
                attrs["current_ma"] = round(c, 1)
                attrs["current"] = attrs["current_a"]
            except (TypeError, ValueError):
                pass

        energy_val = _first_valid_dps(self, "17", "add_ele", "energy")
        if energy_val is not None:
            try:
                e = float(energy_val)
                attrs["total_energy_kwh"] = round(e / 100.0, 3) if e > 500 else round(e, 3)
                attrs["energy"] = attrs["total_energy_kwh"]
            except (TypeError, ValueError):
                pass

        # Atributos de aspiración
        status = self.dps("5")
        if status is not None:
            attrs["vacuum_status"] = status

        mode = self.dps("3")
        if mode is not None:
            attrs["vacuum_mode"] = mode

        clean_time = _first_valid_dps(self, "17", "clean_time", "time")
        if clean_time is not None and "total_energy_kwh" not in attrs:
            attrs["clean_time"] = clean_time

        clean_area = _first_valid_dps(self, "16", "clean_area", "area")
        if clean_area is not None:
            attrs["clean_area"] = clean_area

        return attrs

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
