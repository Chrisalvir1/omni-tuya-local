from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_REGION,
    CONF_VERSION,
    DEFAULT_REGION,
    DEFAULT_VERSION,
    DEVICE_TYPES,
    DOMAIN,
    EXPORT_DOMAINS,
)
from .cloud import async_fetch_cloud_devices

PROTOCOL_VERSIONS = ["auto", "3.1", "3.3", "3.4", "3.5"]
PROTOCOL_VERSIONS_NO_AUTO = ["3.1", "3.3", "3.4", "3.5"]

DOMAIN_LABELS = {
    "switch": "Interruptor / toma",
    "light": "Luz / dimmer",
    "fan": "Ventilador",
    "lock": "Cerradura",
    "cover": "Cortina / portón",
    "climate": "Aire acondicionado / termostato",
    "sensor": "Sensor numérico",
    "binary_sensor": "Sensor binario",
    "button": "Botón / pulsador",
    "number": "Número editable",
    "text": "Texto editable",
    "vacuum": "Robot aspirador / aspiradora",
    "alarm_control_panel": "Panel de alarma",
    "humidifier": "Humidificador",
}


class OmniTuyaLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _cloud_devices: list[dict[str, Any]] = []
    _selected_cloud_device: dict[str, Any] | None = None
    _device_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            mode = user_input["setup_mode"]
            if mode == "cloud_device":
                return await self.async_step_cloud_credentials()
            if mode == "manual_device":
                return await self.async_step_local_device()

        fields: OrderedDict[vol.Marker, Any] = OrderedDict()
        fields[vol.Required("setup_mode")] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(
                        value="cloud_device",
                        label="Agregar desde Tuya Cloud (recomendado — trae local key automáticamente)",
                    ),
                    SelectOptionDict(
                        value="manual_device",
                        label="Agregar manualmente (necesitas device_id, local_key e IP)",
                    ),
                ],
                mode=SelectSelectorMode.LIST,
            )
        )
        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields))

    async def async_step_cloud_credentials(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                devices = await async_fetch_cloud_devices(
                    self.hass,
                    user_input[CONF_API_KEY],
                    user_input[CONF_API_SECRET],
                    user_input.get(CONF_REGION, DEFAULT_REGION),
                    "",
                )
                self._cloud_devices = [d for d in devices if d.get(CONF_LOCAL_KEY)]
                if not self._cloud_devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_choose_cloud_device()
            except Exception:
                errors["base"] = "cloud_error"

        schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default=DEFAULT_REGION): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value="us", label="América (us)"),
                            SelectOptionDict(value="eu", label="Europa (eu)"),
                            SelectOptionDict(value="cn", label="China (cn)"),
                            SelectOptionDict(value="in", label="India (in)"),
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_SECRET): str,
            }
        )
        return self.async_show_form(
            step_id="cloud_credentials",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_choose_cloud_device(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            self._selected_cloud_device = next(
                d for d in self._cloud_devices if d[CONF_DEVICE_ID] == device_id
            )
            return await self.async_step_search_device()

        options = [
            SelectOptionDict(
                value=d[CONF_DEVICE_ID],
                label="{name} — {model} [{id}]".format(
                    name=d.get("name") or d[CONF_DEVICE_ID],
                    model=d.get("product_name") or d.get("domain") or "Tuya",
                    id=d[CONF_DEVICE_ID][:8],
                ),
            )
            for d in sorted(self._cloud_devices, key=lambda item: (item.get("name") or "").lower())
        ]
        return self.async_show_form(
            step_id="choose_cloud_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    )
                }
            ),
        )

    async def async_step_search_device(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            device = dict(self._selected_cloud_device or {})
            # Ejecutar búsqueda en executor con timeout garantizado
            try:
                found = await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        _find_tuya_device, device[CONF_DEVICE_ID]
                    ),
                    timeout=12,
                )
            except asyncio.TimeoutError:
                found = {}

            if found.get("ip"):
                device[CONF_HOST] = found["ip"]
                device["ip"] = found["ip"]
            if found.get("version"):
                device[CONF_VERSION] = str(found["version"])
            self._device_data = device
            return await self.async_step_local_device()

        return self.async_show_form(
            step_id="search_device",
            data_schema=vol.Schema({}),
            description_placeholders={
                "device_name": (self._selected_cloud_device or {}).get("name", "Tuya"),
                "device_id": (self._selected_cloud_device or {}).get(CONF_DEVICE_ID, ""),
            },
        )

    async def async_step_local_device(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        defaults = dict(self._device_data)

        if user_input is not None:
            config = dict(defaults)
            config.update(user_input)

            # Validar IP si se proporcionó
            host = config.get(CONF_HOST, "").strip()
            if host and not _is_valid_ip(host):
                errors[CONF_HOST] = "invalid_ip"
            else:
                protocol = config.get(CONF_VERSION, DEFAULT_VERSION)
                if protocol == "auto":
                    ok, detected = await _async_test_any_protocol(self.hass, config)
                    config[CONF_VERSION] = detected if ok else str(defaults.get(CONF_VERSION) or "3.3")
                elif host:
                    # Solo probar si hay IP configurada
                    await _async_test_tuya_connection(self.hass, config, protocol)

                await self.async_set_unique_id(config[CONF_DEVICE_ID])
                self._abort_if_unique_id_configured()
                self._device_data = config
                return await self.async_step_device_details()

        has_cloud_data = bool(defaults.get(CONF_LOCAL_KEY))
        hint = (
            "La nube ya trajo la ficha del dispositivo. Revisa la IP local y protocolo."
            if has_cloud_data
            else "Completa todos los campos. Puedes dejar la IP vacía y configurarla después."
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")): str,
                vol.Optional(CONF_HOST, default=defaults.get(CONF_HOST) or defaults.get("ip") or ""): str,
                vol.Required(CONF_LOCAL_KEY, default=defaults.get(CONF_LOCAL_KEY, "")): str,
                vol.Required(CONF_VERSION, default=str(defaults.get(CONF_VERSION) or DEFAULT_VERSION)): vol.In(PROTOCOL_VERSIONS),
                vol.Required("domain", default=defaults.get("domain") or "switch"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=domain, label=DOMAIN_LABELS.get(domain, domain))
                            for domain in EXPORT_DOMAINS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_DEVICE_TYPE, default=defaults.get(CONF_DEVICE_TYPE) or "generic"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=dt, label=meta["label"])
                            for dt, meta in DEVICE_TYPES.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="local_device",
            data_schema=schema,
            errors=errors,
            description_placeholders={"hint": hint},
        )

    async def async_step_device_details(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            config = dict(self._device_data)
            config["name"] = user_input[CONF_NAME]
            return self.async_create_entry(title=config["name"], data=config)

        default_name = (
            self._device_data.get("name")
            or self._device_data.get(CONF_DEVICE_ID)
            or "Tuya Local"
        )
        return self.async_show_form(
            step_id="device_details",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=default_name): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OmniTuyaLocalOptionsFlow(config_entry)


class OmniTuyaLocalOptionsFlow(config_entries.OptionsFlow):
    """
    Options flow:
      Paso 1 – Seleccionar dispositivo (muestra IP actual y estado)
      Paso 2 – Editar IP, local_key, protocolo, dominio y tipo
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._selected_device_id: str | None = None
        self._devices: dict[str, dict] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Mostrar dropdown con todos los dispositivos y sus IPs actuales."""
        from .storage import TuyaDeviceStore

        store = TuyaDeviceStore(self.hass)
        await store.async_load()
        self._devices = store.all()

        if not self._devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            self._selected_device_id = user_input["device_id"]
            return await self.async_step_edit_device()

        device_options = {
            dev_id: "{name}  ·  IP: {ip}  ·  v{ver}".format(
                name=conf.get("name", dev_id),
                ip=conf.get("host") or conf.get("ip") or "sin IP",
                ver=conf.get("version") or "?",
            )
            for dev_id, conf in self._devices.items()
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("device_id"): vol.In(device_options)}),
            description_placeholders={"count": str(len(self._devices))},
        )

    async def async_step_edit_device(self, user_input: dict[str, Any] | None = None):
        """Editar IP, local_key, protocolo, dominio y tipo del dispositivo seleccionado."""
        from .storage import TuyaDeviceStore

        store = TuyaDeviceStore(self.hass)
        await store.async_load()
        dev = store.get(self._selected_device_id) or {}

        errors: dict[str, str] = {}

        if user_input is not None:
            ip = user_input.get(CONF_HOST, "").strip()

            if ip and not _is_valid_ip(ip):
                errors[CONF_HOST] = "invalid_ip"
            else:
                updated = dict(dev)
                updated[CONF_HOST] = ip
                updated["ip"] = ip
                updated[CONF_NAME] = user_input.get(CONF_NAME) or updated.get(CONF_NAME) or self._selected_device_id
                updated["name"] = updated[CONF_NAME]
                updated[CONF_VERSION] = user_input.get(CONF_VERSION) or updated.get(CONF_VERSION) or "3.3"
                updated["domain"] = user_input.get("domain") or updated.get("domain") or "switch"
                updated[CONF_DEVICE_TYPE] = user_input.get(CONF_DEVICE_TYPE) or updated.get(CONF_DEVICE_TYPE) or "generic"

                # Actualizar local_key si se proporcionó
                new_local_key = user_input.get(CONF_LOCAL_KEY, "").strip()
                if new_local_key:
                    updated[CONF_LOCAL_KEY] = new_local_key

                await store.add(updated)

                # Recargar coordinator para que la nueva config tome efecto inmediatamente
                try:
                    coordinator = self.hass.data[DOMAIN][self._config_entry.entry_id]
                    await coordinator.async_reload_devices()
                except Exception:
                    pass

                return self.async_create_entry(title="", data={})

        current_ip = dev.get("host") or dev.get("ip") or ""
        current_version = str(dev.get(CONF_VERSION) or "3.3")
        current_domain = dev.get("domain") or "switch"
        current_device_type = dev.get(CONF_DEVICE_TYPE) or "generic"
        local_key = dev.get(CONF_LOCAL_KEY, "")
        local_key_masked = (
            f"{'*' * max(0, len(local_key) - 4)}{local_key[-4:]}"
            if len(local_key) >= 4 else "****"
        )

        return self.async_show_form(
            step_id="edit_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=dev.get("name") or self._selected_device_id): str,
                    vol.Optional(CONF_HOST, default=current_ip): str,
                    vol.Optional(CONF_LOCAL_KEY, default=""): str,
                    vol.Required(CONF_VERSION, default=current_version): vol.In(PROTOCOL_VERSIONS_NO_AUTO),
                    vol.Required("domain", default=current_domain): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=d, label=DOMAIN_LABELS.get(d, d))
                                for d in EXPORT_DOMAINS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_DEVICE_TYPE, default=current_device_type): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=dt, label=meta["label"])
                                for dt, meta in DEVICE_TYPES.items()
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={
                "device_name": dev.get("name", self._selected_device_id or ""),
                "device_id": self._selected_device_id or "",
                "current_ip": current_ip or "sin IP configurada",
                "current_version": current_version,
                "current_domain": DOMAIN_LABELS.get(current_domain, current_domain),
                "current_device_type": DEVICE_TYPES.get(current_device_type, DEVICE_TYPES["generic"])["label"],
                "local_key_masked": local_key_masked,
            },
            errors=errors,
        )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_valid_ip(ip: str) -> bool:
    """Validar formato de IP (IPv4)."""
    import re
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    return all(0 <= int(part) <= 255 for part in ip.split("."))


def _find_tuya_device(device_id: str) -> dict[str, Any]:
    """Buscar dispositivo Tuya en la red local con TinyTuya."""
    try:
        import tinytuya
        found = tinytuya.deviceScan(False, 6) or {}
    except Exception:
        return {}

    for ip, details in found.items():
        if details.get("id") == device_id or details.get("gwId") == device_id:
            return {"ip": ip, "version": details.get("ver")}
    return {}


async def _async_test_any_protocol(hass, config: dict[str, Any]) -> tuple[bool, str]:
    for protocol in ("3.5", "3.4", "3.3", "3.1"):
        if await _async_test_tuya_connection(hass, config, protocol):
            return True, protocol
    return False, DEFAULT_VERSION


async def _async_test_tuya_connection(hass, config: dict[str, Any], protocol: str) -> bool:
    try:
        return await asyncio.wait_for(
            hass.async_add_executor_job(_test_tuya_connection, config, protocol),
            timeout=8,
        )
    except Exception:
        return False


def _test_tuya_connection(config: dict[str, Any], protocol: str) -> bool:
    try:
        import tinytuya

        device = tinytuya.Device(
            dev_id=config[CONF_DEVICE_ID],
            address=config[CONF_HOST],
            local_key=config[CONF_LOCAL_KEY],
            version=float(protocol),
        )
        device.set_socketPersistent(False)
        raw = device.status()
        return bool(isinstance(raw, dict) and "dps" in raw)
    except Exception:
        return False
