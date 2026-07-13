from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .models import TuyaDeviceConfig

_LOGGER = logging.getLogger(__name__)

# TinyTuya's socket timeout is 3 seconds. The outer asyncio timeout must be
# longer than that (and include TinyTuya's socket retry) or HA cancels healthy,
# but slow, Wi-Fi devices before the LAN request can finish.
_TUYA_TIMEOUT = 8
_MAX_STATUS_ATTEMPTS = 2
# A single lost Wi-Fi packet must not flip every entity to unavailable.
_UNAVAILABLE_AFTER_FAILURES = 3


class OmniTuyaDevice:
    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        on_push: Any | None = None
    ) -> None:
        self.hass = hass
        self.config = TuyaDeviceConfig.from_dict(config)
        self.device_id = self.config.device_id
        self._on_push = on_push
        self._tuya = None
        self._available = False
        self._last_dps: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._consecutive_failures: int = 0
        self._last_error_detail: str = ""
        self._runtime_version: str | None = None
        self._detected_protocol_version: str | None = None
        self._probed_config_version: str = ""
        
        self._listening = False
        if self.config.device_type == "alarm_kit":
            self._start_push_listener()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def dps(self) -> dict[str, Any]:
        return dict(self._last_dps)

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def last_error_detail(self) -> str:
        return self._last_error_detail

    @property
    def detected_protocol_version(self) -> str | None:
        """A verified LAN protocol that the coordinator should persist."""
        return self._detected_protocol_version

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
            self._runtime_version = None
            self._detected_protocol_version = None
            self._probed_config_version = ""
            _LOGGER.info(
                "Device %s config updated (IP: %s → %s, Ver: %s → %s), reconnecting",
                self.device_id, old_host, self.config.host, old_version, self.config.version,
            )

    def _build_tuya(self, version: str | None = None):
        """Construir cliente TinyTuya. Siempre crea instancia nueva."""
        import tinytuya

        if not self.config.has_host:
            raise ValueError(f"Device {self.device_id} has no IP address configured")

        effective_version = version or self._runtime_version or self.config.version or "3.3"
        if self.config.is_sub_device:
            parent = tinytuya.Device(
                dev_id=self.config.gateway_id,
                address=self.config.effective_host,
                local_key=self.config.gateway_local_key or self.config.local_key,
                version=float(effective_version),
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
                version=float(effective_version),
            )
            device.set_socketPersistent(False)
            device.set_socketTimeout(3.0)
            device.set_socketRetryLimit(1)
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
                self._last_error_detail = ""
                return dict(raw["dps"])
            # TinyTuya reports normal LAN packet loss as a dictionary rather
            # than raising. Keep the reason for diagnostics but avoid emitting
            # a warning for every retry/poll cycle.
            self._last_error_detail = str(raw.get("Payload") or raw.get("Error") or raw)
            _LOGGER.debug("Tuya device %s status returned no dps: %s", self.device_id, raw)
        else:
            self._last_error_detail = str(raw)
            _LOGGER.debug("Tuya device %s status returned empty response: %s", self.device_id, raw)
        return None

    def _mark_online(self) -> None:
        self._available = True
        self._consecutive_failures = 0
        self._last_error_detail = ""

    def _mark_failure(self, reason: Exception | str | None) -> None:
        """Apply availability hysteresis so brief Wi-Fi loss does not flap."""
        self._consecutive_failures += 1
        detail = str(reason or self._last_error_detail or "no DPS response")
        self._last_error_detail = detail
        if self._consecutive_failures >= _UNAVAILABLE_AFTER_FAILURES:
            if self._available and self._consecutive_failures == _UNAVAILABLE_AFTER_FAILURES:
                _LOGGER.warning(
                    "Device %s (%s) unavailable after %d failed polls: %s",
                    self.device_id, self.config.host, self._consecutive_failures, detail,
                )
            self._available = False
        else:
            _LOGGER.debug(
                "Transient LAN failure for %s (%d/%d before unavailable): %s",
                self.device_id, self._consecutive_failures,
                _UNAVAILABLE_AFTER_FAILURES, detail,
            )


    def _sync_set_status(self, value: bool, dps_id: int) -> None:
        device = self._get_or_build_tuya()
        device.set_status(value, dps_id)

    def _sync_set_value(self, dps_id: int, value: Any) -> None:
        device = self._get_or_build_tuya()
        device.set_value(dps_id, value)

    def _sync_set_values(self, dps_dict: dict[str, Any]) -> None:
        device = self._get_or_build_tuya()
        device.set_multiple_values(dps_dict)

    def _sync_probe_protocol_versions(self) -> tuple[str, dict[str, Any]] | None:
        """Try alternative Tuya LAN protocol versions once after error 914."""
        for version in ("3.5", "3.4", "3.3", "3.1"):
            if version == str(self.config.version):
                continue
            try:
                candidate = self._build_tuya(version)
                raw = candidate.status()
                if isinstance(raw, dict) and isinstance(raw.get("dps"), dict):
                    self._tuya = candidate
                    return version, dict(raw["dps"])
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Protocol %s did not work for %s: %s", version, self.device_id, err)
        return None

    async def async_status(self) -> dict[str, Any]:
        """Obtener estado del dispositivo con reintentos y timeout."""
        async with self._lock:
            if not self.config.has_host:
                self._available = False
                return self.dps

            last_err: Exception | None = None
            for attempt in range(_MAX_STATUS_ATTEMPTS):
                try:
                    dps = await asyncio.wait_for(
                        self.hass.async_add_executor_job(self._sync_status),
                        timeout=_TUYA_TIMEOUT,
                    )
                    if dps is not None:
                        self._last_dps.update(dps)
                        self._mark_online()
                        return self.dps
                    raise ConnectionError(self._last_error_detail or "Empty or invalid status response")
                except asyncio.TimeoutError as err:
                    last_err = err
                    _LOGGER.debug(
                        "Timeout polling %s (attempt %d/%d)",
                        self.device_id, attempt + 1, _MAX_STATUS_ATTEMPTS,
                    )
                    self._invalidate_client()
                except Exception as err:
                    last_err = err
                    _LOGGER.debug(
                        "Poll error for %s (attempt %d/%d): %s",
                        self.device_id, attempt + 1, _MAX_STATUS_ATTEMPTS, err,
                    )
                    self._invalidate_client()
                if attempt + 1 < _MAX_STATUS_ATTEMPTS:
                    await asyncio.sleep(0.2)

            # Error 914 means the device answered on the LAN but rejected the
            # encryption framing. Protocol changes are safe to test once; a
            # missing/rotated local key will still fail all candidates.
            if (
                "Check device key or version" in self._last_error_detail
                and self._probed_config_version != str(self.config.version)
            ):
                self._probed_config_version = str(self.config.version)
                try:
                    probe = await asyncio.wait_for(
                        self.hass.async_add_executor_job(self._sync_probe_protocol_versions),
                        timeout=16,
                    )
                except asyncio.TimeoutError:
                    probe = None
                if probe is not None:
                    version, dps = probe
                    self._runtime_version = version
                    self._detected_protocol_version = version
                    self._last_dps.update(dps)
                    self._mark_online()
                    _LOGGER.info(
                        "Device %s responded with Tuya protocol %s; saving detected version",
                        self.device_id, version,
                    )
                    return self.dps

            self._mark_failure(last_err)
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
                self._mark_online()
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending set_status to %s dps %s", self.device_id, dps_id
                )
                self._invalidate_client()
                self._mark_failure("Timeout sending set_status")
                return False
            except Exception as err:
                _LOGGER.error(
                    "Command failed for %s dps %s: %s", self.device_id, dps_id, err
                )
                self._invalidate_client()
                self._mark_failure(err)
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
                self._mark_online()
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending value to %s dps %s", self.device_id, dps_id
                )
                self._invalidate_client()
                self._mark_failure("Timeout sending value")
                return False
            except Exception as err:
                _LOGGER.error(
                    "Value command failed for %s dps %s: %s", self.device_id, dps_id, err
                )
                self._invalidate_client()
                self._mark_failure(err)
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
                self._mark_online()
                return True
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout sending multiple values to %s: %s", self.device_id, dps_dict
                )
                self._invalidate_client()
                self._mark_failure("Timeout sending multiple values")
                return False
            except Exception as err:
                _LOGGER.error(
                    "Multiple values command failed for %s (%s): %s", self.device_id, dps_dict, err
                )
                self._invalidate_client()
                self._mark_failure(err)
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
        self._listening = False
        if self._tuya:
            try:
                self._tuya.close()
            except Exception:
                pass
            self._tuya = None

    def _start_push_listener(self) -> None:
        if not self._listening:
            self._listening = True
            import threading
            threading.Thread(
                target=self._push_listener_loop,
                daemon=True,
                name=f"TuyaPush_{self.device_id}"
            ).start()
            _LOGGER.info("Started Tuya TCP Push Listener for %s", self.device_id)

    def _push_listener_loop(self) -> None:
        """Hilo dedicado (daemon) para escuchar eventos push TCP en tiempo real."""
        import time
        while self._listening:
            if not self.config.has_host:
                time.sleep(2)
                continue

            try:
                # _get_or_build_tuya will create the device if None
                dev = self._get_or_build_tuya()
                dev.set_socketPersistent(True)
                dev.set_socketTimeout(5.0)

                # Enviar status inicial para forzar la apertura del socket
                try:
                    dev.status()
                except Exception:
                    pass

                while self._listening:
                    try:
                        data = dev.receive()
                        if data and isinstance(data, dict) and "dps" in data:
                            dps = data["dps"]
                            self._last_dps.update(dps)
                            self._available = True
                            self._consecutive_failures = 0
                            
                            _LOGGER.debug("TCP Push received from %s: %s", self.device_id, dps)
                            
                            if self._on_push:
                                self.hass.loop.call_soon_threadsafe(
                                    self._on_push, self.device_id, dps
                                )
                    except Exception as err:
                        if self._listening:
                            _LOGGER.debug("Push listener error for %s: %s", self.device_id, err)
                            self._invalidate_client()
                            break  # Reconstruir socket
            except Exception as err:
                _LOGGER.debug("Push listener connect error for %s: %s", self.device_id, err)
                time.sleep(5)
