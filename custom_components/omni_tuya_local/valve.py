"""Native Home Assistant valve entities for explicitly mapped Tuya DPS."""
from __future__ import annotations

from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OmniTuyaLocalCoordinator
from .entity import OmniTuyaEntity
from .pet_feeder import function_id


def _bool_schema(value: Any) -> bool:
    return str(value or "").strip().lower() in {"bool", "boolean"}


def valve_profile(config: dict[str, Any], raw_dps: dict[str, Any]) -> tuple[str, bool, bool] | None:
    """Resolve a valve only from explicit domain and a reported boolean DPS.

    Tuya products have no universal valve DP. Require the user to classify the
    device as ``valve`` and require either a matching Tuya product function or
    an explicit ``device_class: valve`` descriptor in ``dps_map``.
    """
    if str(config.get("domain", "")).lower() != "valve":
        return None
    functions = config.get("tuya_functions") or []
    for function in functions:
        if not isinstance(function, dict):
            continue
        code = str(function.get("code") or function.get("identifier") or "").lower()
        dp_id = function_id(function)
        if code not in {"switch", "valve_switch"} or not dp_id or not _bool_schema(function.get("type")):
            continue
        reported = raw_dps.get(dp_id)
        if reported is None and dp_id.isdigit():
            reported = raw_dps.get(int(dp_id))
        if isinstance(reported, bool):
            return dp_id, True, False
    for dp_id, descriptor in (config.get("dps_map") or {}).items():
        if not str(dp_id).isdigit() or not isinstance(descriptor, dict):
            continue
        if str(descriptor.get("device_class", "")).lower() != "valve":
            continue
        reported = raw_dps.get(str(dp_id))
        if reported is None and str(dp_id).isdigit():
            reported = raw_dps.get(int(dp_id))
        if reported is None:
            continue
        open_value = descriptor.get("open_value", True)
        closed_value = descriptor.get("closed_value", False)
        if open_value != closed_value and reported in (open_value, closed_value):
            return str(dp_id), open_value, closed_value
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: OmniTuyaLocalCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    async def add_new_entities() -> None:
        entities = []
        for config in coordinator.store.all().values():
            device_id = str(config.get("device_id") or "")
            raw_dps = (coordinator.data or {}).get("dps", {}).get(device_id, {})
            if not isinstance(raw_dps, dict):
                raw_dps = {}
            profile = valve_profile(config, raw_dps)
            if profile is None or device_id in known:
                continue
            known.add(device_id)
            entities.append(OmniTuyaValve(coordinator, config, *profile))
        if entities:
            async_add_entities(entities)

    coordinator.register_entity_refresh_callback(add_new_entities)
    await add_new_entities()


class OmniTuyaValve(OmniTuyaEntity, ValveEntity):
    """Valve switch with no guessed DPS IDs or states."""

    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(self, coordinator, config, dps_id: str, open_value: Any, closed_value: Any) -> None:
        super().__init__(coordinator, config, dps_id)
        self._open_value = open_value
        self._closed_value = closed_value
        self._attr_unique_id = f"{DOMAIN}_{config['device_id']}_valve"
        self._attr_icon = "mdi:valve"

    @property
    def is_open(self) -> bool | None:
        value = self.dps(self.dps_id)
        if value is None:
            return None
        if value == self._open_value:
            return True
        if value == self._closed_value:
            return False
        return None

    async def async_open_valve(self) -> None:
        if isinstance(self._open_value, bool) and isinstance(self._closed_value, bool):
            await self.coordinator.async_set_status(self.device_id, self._open_value, int(self.dps_id))
        else:
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), self._open_value)

    async def async_close_valve(self) -> None:
        if isinstance(self._closed_value, bool) and isinstance(self._open_value, bool):
            await self.coordinator.async_set_status(self.device_id, self._closed_value, int(self.dps_id))
        else:
            await self.coordinator.async_set_value(self.device_id, int(self.dps_id), self._closed_value)
