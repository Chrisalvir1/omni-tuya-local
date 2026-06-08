from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN
from .coordinator import OmniTuyaLocalCoordinator


class OmniTuyaEntity(CoordinatorEntity[OmniTuyaLocalCoordinator]):
    _attr_has_entity_name = True
    _attr_should_poll = False  # el coordinator se encarga del polling

    def __init__(self, coordinator: OmniTuyaLocalCoordinator, config: dict, suffix: str = "") -> None:
        super().__init__(coordinator)
        self.config = config
        self.device_id = config["device_id"]
        self.dps_id = str(suffix or "1")
        unique_suffix = "" if self.dps_id == "1" else f"_{self.dps_id}"
        self._attr_unique_id = f"{DOMAIN}_{self.device_id}{unique_suffix}"

        device_type = config.get("device_type") or "generic"
        type_meta = DEVICE_TYPES.get(device_type, DEVICE_TYPES["generic"])

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=config.get("name") or self.device_id,
            manufacturer="Tuya",
            # model: product_name → tipo legible → dominio
            model=(
                config.get("product_name")
                or type_meta.get("label")
                or config.get("domain")
                or "Tuya Local"
            ),
            # sw_version muestra la versión del protocolo LAN en la tarjeta del dispositivo
            sw_version=f"LAN {config.get('version') or '3.3'}",
            # serial_number = device_id para identificación rápida en la UI
            serial_number=self.device_id,
            # configuration_url apunta a la IP local del dispositivo
            configuration_url=(
                f"http://{config.get('host')}"
                if config.get("host")
                else None
            ),
        )

    @property
    def available(self) -> bool:
        return self.coordinator.is_available(self.device_id)

    @property
    def raw_dps(self) -> dict:
        return (self.coordinator.data or {}).get("dps", {}).get(self.device_id, {})

    def dps(self, dps_id: str | int | None = None):
        return self.coordinator.dps_value(self.device_id, str(dps_id or self.dps_id))

    @property
    def extra_state_attributes(self) -> dict:
        config = self.coordinator.get_device_config(self.device_id) or self.config
        host = config.get("host") or config.get("ip") or ""
        local_key = config.get("local_key", "")
        # Ofuscar local_key: mostrar solo los últimos 4 caracteres
        local_key_masked = (
            f"{'*' * max(0, len(local_key) - 4)}{local_key[-4:]}"
            if len(local_key) >= 4
            else "****"
        )
        attrs = {
            "device_id": self.device_id,
            "ip": host,
            "host": host,
            "protocol_version": config.get("version"),
            "product_name": config.get("product_name"),
            "product_id": config.get("product_id"),
            "category": config.get("category"),
            "device_type": config.get("device_type"),
            "local_key": local_key_masked,
            "poll_interval": config.get("poll_interval"),
            "raw_dps": self.raw_dps,
        }
        # Datos de gateway para sub-devices zigbee/BLE
        if config.get("gateway_id"):
            attrs["gateway_id"] = config.get("gateway_id")
            attrs["node_id"] = config.get("node_id")
            attrs["gateway_host"] = config.get("gateway_host")
        return attrs

    @property
    def icon(self) -> str | None:
        device_type = self.config.get("device_type") or "generic"
        return DEVICE_TYPES.get(device_type, DEVICE_TYPES["generic"]).get("icon")

    @property
    def name(self) -> str | None:
        """Nombre amigable de la entidad."""
        if self.dps_id == "1":
            return None
        return f"DPS {self.dps_id}"
