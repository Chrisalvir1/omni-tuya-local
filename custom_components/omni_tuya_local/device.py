from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .models import TuyaDeviceConfig

_LOGGER = logging.getLogger(__name__)

# Tiempo máximo de espera para cualquier operación LAN
_TUYA_TIMEOUT = 5
# Reintentos antes de marcar unavailable
_MAX_STATUS_RETRIES = 3


class OmniTuyaDevice:
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self.hass = hass
        self.config = TuyaDeviceConfig.from_dict(config)
        self.device_id = self.config.device_id
        self._tuya = None
        self._available = False
        self._last_dps: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._consecutive_failures: int = 0

    @property
    def available(self) -> bool:
        return self._available

    @property
    def dps(self) -> dict[str, Any]:
        return dict(self._last_dps)

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def update_config(self, config: dict[str, Any]) -> None:
        """Actualizar configuración del dispositivo (ej: nueva IP, versión, o local key) sin reconstruir."""
        old_host = self.config.host
        old_version = self.config.version
        old_local_key = self.config.local_key
        
        self.config = TuyaDeviceConfig.from_dict(config)
        
        if (
            self.config.host != old_host
            or self.config.version != old_version
            or self.config.local_key != old_local_key
        ):
            # IP, versión o local key cambió — invalidar cliente para forzar reconexión
            self._tuya = None
            _LOGGER.info(
                "Device %s config updated (IP: %s → %s, Ver: %s → %s), reconnecting",
                self.device_id, old_host, self.config.host, old_version, self.config.version,
            )

    def _build_tuya(self):
        """Construir cliente TinyTuya. Siempre crea instancia nueva."""
        import tinytuya

        if not self.config.has_host:
            raise ValueError(f"Device {self.device_id} has no IP address configured")

        if self.config.is_sub_device:
            parent = tinytuya.Device(
                dev_id=self.config.gateway_id,
                address=self.config.effective_host,
                local_key=self.config.gateway_local_key or self.config.local_key,
                version=float(self.config.version or 3.3),
            )
            parent.set_socketPersistent(False)
            parent.set_socketTimeout(5.0)
            parent.set_socketRetryLimit(3)
            device = tinytuya.Device(
                dev_id=self.device_id,
                cid=self.config.node_id,
                parent=parent,
            )
        else:
            device = tinytuya.Device(
                dev_id=self.device_id,
                address=self.config.host,
                local_key=self.config.local_key,
                version=float(self.config.version or 3.3),
            )
            device.set_socketPersistent(True)
            device.set_socketTimeout(3.0)
            device.set_socketRetryLimit(2)
        return device

    def _get_or_build_tuya(self):
        """Obtener cliente existente o construir uno nuevo."""
        if self._tuya is None:
            self._tuya = self._build_tuya()
        return self._tuya

    def _invalidate_client(self) -> None:
        """Descartar cliente actual para que se reconstruya en el próximo uso."""
        self._tuya = None

    def _sync_status(self) -> dict[str, Any] | None:
        """Llamada síncrona a tinytuya.status(). Retorna dps o None."""
        device = self._get_or_build_tuya()
        raw = device.status()
        if raw and isinstance(raw, dict):
            if "dps" in raw:
                return dict(raw["dps"])
            _LOGGER.warning("Tuya device %s status returned no dps. Raw response: %s", self.device_id, raw)
        else:
            _LOGGER.warning("Tuya device %s status returned empty or non-dict response: %s", self.device_id, raw)
        return None


    def _sync_set_status(self, value: bool, dps_id: int) -> None:
        device = self._get_or_build_tuya()
        device.set_status(value, dps_id)

    def _sync_set_value(self, dps_id: int, value: Any) -> None:
        device = self._get_or_build_tuya()
        device.set_value(dps_id, value)

    def _sync_set_values(self, dps_dict: dict[str, Any]) -> None:
        device = self._get_or_build_tuya()
        device.set_multiple_values(dps_dict)

    async def async_status(self) -> dict[str, Any]:
        """Obtener estado del dispositivo con reintentos y timeout."""
        async with self._lock:
            if not self.config.has_host:
                self._available = False
                return self.dps

            last_err: Exception | None = None
            for attempt in range(_MAX_STATUS_RETRIES):
                try:
                    dps = await asyncio.wait_for(
                        self.hass.async_add_executor_job(self._sync_status),
                        timeout=_TUYA_TIMEOUT,
                    )
                    if dps is not None:
                        self._last_dps.update(dps)
                        self._available = True
                        self._consecutive_failures = 0
                        return self.dps
                    raise ConnectionError("Empty or invalid status response from Tuya device")
                except asyncio.TimeoutError as err:
                    last_err = err
                    _LOGGER.debug(
                        "Timeout polling %s (attempt %d/%d)",
                        self.device_id, attempt + 1, _MAX_STATUS_RETRIES,
                    )
                    self._invalidate_client()
                except Exception as err:
                    last_err = err
                    _LOGGER.debug(
                        "Poll error for %s (attempt %d/%d): %s",
                        self.device_id, attempt + 1, _MAX_STATUS_RETRIES, err,
                    )
                    self._invalidate_client()

            # Todos los reintentos fallaron
            self._consecutive_failures += 1
            if self._available:
                _LOGGER.warning(
                    "Device %s (%s) became unavailable: %s",
                    self.device_id, self.config.host, last_err,
                )
            self._available = False
            return self.dps

    async def async_set_status(self, value: bool, dps_id: int = 1) -> bool:
        """Enviar comando on/off al dispositivo."""
        async with self._lock:
            if not self.config.has_host:
                _LOGGER.error("Device %s has no IP — cannot send command", self.device_id)
                return False
            try:
                await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        lambda: self._sync_set_status(value, dps_id)
                    ),
                    timeout=_TUYA_TIMEOUT,
                )
                self._last_dps[str(dps_id)] = value
                self._available = True
                self._consecutive_failures = 0
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending set_status to %s dps %s", self.device_id, dps_id
                )
                self._invalidate_client()
                return False
            except Exception as err:
                _LOGGER.error(
                    "Command failed for %s dps %s: %s", self.device_id, dps_id, err
                )
                self._invalidate_client()
                self._available = False
                return False

    async def async_set_value(self, dps_id: int, value: Any) -> bool:
        """Enviar un valor arbitrario a un DPS."""
        async with self._lock:
            if not self.config.has_host:
                _LOGGER.error("Device %s has no IP — cannot send value", self.device_id)
                return False
            try:
                await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        lambda: self._sync_set_value(dps_id, value)
                    ),
                    timeout=_TUYA_TIMEOUT,
                )
                self._last_dps[str(dps_id)] = value
                self._available = True
                self._consecutive_failures = 0
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending value to %s dps %s", self.device_id, dps_id
                )
                self._invalidate_client()
                return False
            except Exception as err:
                _LOGGER.error(
                    "Value command failed for %s dps %s: %s", self.device_id, dps_id, err
                )
                self._invalidate_client()
                self._available = False
                return False

    async def async_set_values(self, dps_dict: dict[str, Any]) -> bool:
        """Enviar múltiples valores DPS al dispositivo en un solo payload."""
        if not dps_dict:
            return True
        async with self._lock:
            if not self.config.has_host:
                _LOGGER.error("Device %s has no IP — cannot send values", self.device_id)
                return False
            try:
                stringified_dict = {str(k): v for k, v in dps_dict.items()}
                await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        lambda: self._sync_set_values(stringified_dict)
                    ),
                    timeout=_TUYA_TIMEOUT,
                )
                for dps_id, value in stringified_dict.items():
                    self._last_dps[dps_id] = value
                self._available = True
                self._consecutive_failures = 0
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending multiple values to %s: %s", self.device_id, dps_dict
                )
                self._invalidate_client()
                return False
            except Exception as err:
                _LOGGER.error(
                    "Multiple values command failed for %s (%s): %s", self.device_id, dps_dict, err
                )
                self._invalidate_client()
                self._available = False
                return False

    async def async_fetch_raw_dps(self) -> dict[str, Any]:
        """Obtener todos los DPS en tiempo real (para diagnóstico)."""
        async with self._lock:
            if not self.config.has_host:
                return {"error": "no_host"}
            try:
                def _get_raw():
                    dev = self._get_or_build_tuya()
                    return dev.status()
                raw = await asyncio.wait_for(
                    self.hass.async_add_executor_job(_get_raw),
                    timeout=_TUYA_TIMEOUT,
                )
                if raw and isinstance(raw, dict):
                    return raw
                return {"error": "invalid_response", "raw": raw}
            except Exception as err:
                _LOGGER.debug("fetch_raw_dps error for %s: %s", self.device_id, err)
                self._invalidate_client()
                return {"error": str(err)}

    def close(self) -> None:
        """Cerrar la conexión socket persistentemente abierta."""
        if self._tuya:
            try:
                self._tuya.close()
            except Exception:
                pass
            self._tuya = None
