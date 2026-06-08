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

    # Indicar a HA que no requiere código PIN para armar/desarmar
    _attr_code_arm_required = False
    _attr_code_format = None

    def _determine_dps_id(self) -> str:
        """Determinar dinámicamente qué DP controla el estado de la alarma."""
        raw_dps = self.coordinator.dps_value(self.device_id) or {}
        # Lista de candidatos comunes: 123 (eMacros), 113 (chime/ON/OFF), 1 (estándar)
        for cand in ("123", "113", "1"):
            if cand in raw_dps:
                return cand
        return "1"

    @property
    def name(self) -> str:
        return self.config.get("name") or self.device_id

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        dps_id = self._determine_dps_id()
        raw_val = self.dps(dps_id)
        if raw_val is None:
            return AlarmControlPanelState.DISARMED

        value = str(raw_val).lower()
        if value in {"triggered", "alarm", "sos"}:
            return AlarmControlPanelState.TRIGGERED
        
        # Para DPs booleanos (ej. 123)
        if isinstance(raw_val, bool):
            return AlarmControlPanelState.ARMED_AWAY if raw_val else AlarmControlPanelState.DISARMED

        # Para DPs de ON/OFF (ej. 113)
        if value in {"on", "true", "1"}:
            return AlarmControlPanelState.ARMED_AWAY
        if value in {"off", "false", "0"}:
            return AlarmControlPanelState.DISARMED

        # Para DPs con enums de texto estándar
        if value in {"home", "stay", "arm_home"}:
            return AlarmControlPanelState.ARMED_HOME
        if value in {"away", "armed", "arm", "arm_away"}:
            return AlarmControlPanelState.ARMED_AWAY

        return AlarmControlPanelState.DISARMED

    async def _send_command(self, cmd_type: str) -> None:
        dps_id = self._determine_dps_id()
        raw_dps = self.coordinator.dps_value(self.device_id) or {}
        current_val = raw_dps.get(dps_id)

        # Mapear valor según el tipo de dato nativo del DP
        val_to_send: any = "disarmed"
        if cmd_type == "disarm":
            if isinstance(current_val, bool):
                val_to_send = False
            elif str(current_val).upper() in ("ON", "OFF"):
                val_to_send = "OFF"
            else:
                val_to_send = "disarmed"
        elif cmd_type == "arm_home":
            if isinstance(current_val, bool):
                val_to_send = True
            elif str(current_val).upper() in ("ON", "OFF"):
                val_to_send = "ON"
            else:
                val_to_send = "home"
        elif cmd_type == "arm_away":
            if isinstance(current_val, bool):
                val_to_send = True
            elif str(current_val).upper() in ("ON", "OFF"):
                val_to_send = "ON"
            else:
                val_to_send = "away"

        await self.coordinator.async_set_value(self.device_id, int(dps_id), val_to_send)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._send_command("disarm")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._send_command("arm_home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._send_command("arm_away")
