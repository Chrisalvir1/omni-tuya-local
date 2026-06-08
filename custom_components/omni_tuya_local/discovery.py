from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 1))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()


async def async_scan_network(
    hass: HomeAssistant,
    registry_devices: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    registry_devices = registry_devices or []
    found_devices: dict[str, dict[str, Any]] = {}
    local_ip = get_local_ip()
    subnet = ".".join(local_ip.split(".")[:-1])

    def _udp_listen() -> dict[str, bool]:
        seen: dict[str, bool] = {}
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.bind(("", 6667))
            client.settimeout(2)
            import time
            started = time.time()
            while time.time() - started < 5:
                try:
                    _, addr = client.recvfrom(1024)
                    seen[addr[0]] = True
                except Exception:
                    if time.time() - started > 5:
                        break
        finally:
            client.close()
        return seen

    udp_data = await hass.async_add_executor_job(_udp_listen)

    def _tinytuya_scan() -> dict:
        import tinytuya
        return tinytuya.deviceScan(False, 5) or {}

    try:
        scanned = await hass.async_add_executor_job(_tinytuya_scan)
        for ip, info in scanned.items():
            real_id = info.get("id") or info.get("gwId")
            if real_id:
                found_devices[ip] = {
                    "host": ip,
                    "ip": ip,
                    "device_id": real_id,
                    "name": f"Tuya {real_id[:5]}",
                    "version": str(info.get("ver") or 3.3),
                }
    except Exception as err:
        _LOGGER.warning("TinyTuya scan failed: %s", err)

    ips_to_check = set(udp_data.keys())
    ips_to_check.update(device.get("host") or device.get("ip") for device in registry_devices if device.get("host") or device.get("ip"))
    if not found_devices:
        ips_to_check.update(f"{subnet}.{idx}" for idx in range(1, 255))

    semaphore = asyncio.Semaphore(50)

    async def _check(ip: str | None) -> None:
        if not ip or ip in found_devices:
            return
        async with semaphore:
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, 6668), 0.5)
                writer.close()
                await writer.wait_closed()
                del reader
                found_devices[ip] = {
                    "host": ip,
                    "ip": ip,
                    "device_id": f"unknown_{ip.replace('.', '_')}",
                    "name": f"Tuya device at {ip}",
                }
            except Exception:
                return

    await asyncio.gather(*(_check(ip) for ip in ips_to_check))

    final: list[dict[str, Any]] = []
    for ip, device in found_devices.items():
        match = next(
            (
                known
                for known in registry_devices
                if known.get("device_id") == device["device_id"] or known.get("host") == ip or known.get("ip") == ip
            ),
            None,
        )
        if match:
            merged = dict(match)
            merged.update({
                "host": ip,
                "ip": ip,
                "synced": True,
            })
            final.append(merged)
        else:
            device["synced"] = False
            final.append(device)
    return final


class TuyaUDPListener(asyncio.DatagramProtocol):
    """Protocolo UDP para escuchar broadcasts de dispositivos Tuya."""

    def __init__(self, callback: Any) -> None:
        self.callback = callback

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        import json
        import tinytuya
        try:
            decrypted = tinytuya.decrypt_udp(data)
            if decrypted:
                payload = json.loads(decrypted)
                device_id = payload.get("gwId") or payload.get("id")
                ip = payload.get("ip") or addr[0]
                version = payload.get("version") or "3.3"
                if device_id and ip:
                    self.callback(device_id, ip, version)
        except Exception as err:
            _LOGGER.debug("Error decoding Tuya UDP broadcast packet: %s", err)


async def async_start_udp_listener(hass: HomeAssistant, callback: Any) -> list[asyncio.BaseTransport]:
    """Iniciar el listener UDP en los puertos 6666 y 6667 de forma no bloqueante."""
    loop = asyncio.get_running_loop()
    transports = []

    for port in (6666, 6667):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass
            sock.bind(("", port))

            transport, _ = await loop.create_datagram_endpoint(
                lambda: TuyaUDPListener(callback),
                sock=sock,
            )
            transports.append(transport)
            _LOGGER.info("Omni Tuya UDP broadcast listener started on port %s", port)
        except Exception as err:
            _LOGGER.warning("Could not start UDP listener on port %s: %s", port, err)

    return transports
