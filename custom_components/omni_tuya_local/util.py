from __future__ import annotations

from .const import TUYA_BRIGHTNESS_MAX, TUYA_BRIGHTNESS_MIN


def tuya_to_ha_brightness(tuya_value: int) -> int:
    normalized = (int(tuya_value) - TUYA_BRIGHTNESS_MIN) / (TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN)
    return max(0, min(255, int(normalized * 255)))


def ha_to_tuya_brightness(ha_value: int) -> int:
    normalized = int(ha_value) / 255
    return max(TUYA_BRIGHTNESS_MIN, min(TUYA_BRIGHTNESS_MAX, int(normalized * TUYA_BRIGHTNESS_MAX)))


def parse_physical_id(device_id: str) -> tuple[str, int]:
    if "_" in device_id:
        base, maybe_dps = device_id.rsplit("_", 1)
        try:
            return base, int(maybe_dps)
        except ValueError:
            return device_id, 1
    return device_id, 1


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def max_gangs_for_device(config: dict, raw_dps: dict | None = None) -> int:
    """Return maximum number of physical gangs/channels supported by any controller."""
    # 1. Esquema oficial de Tuya Cloud (tuya_functions) - la fuente más precisa
    cloud_gangs = set()
    for func in config.get("tuya_functions") or []:
        if isinstance(func, dict):
            code = str(func.get("code") or func.get("identifier") or "").lower().strip()
            for prefix in ("switch", "power", "outlet", "light"):
                if code == prefix:
                    cloud_gangs.add(1)
                elif code.startswith(f"{prefix}_"):
                    suffix = code[len(prefix) + 1:]
                    if suffix.isdigit() and 1 <= int(suffix) <= 8:
                        cloud_gangs.add(int(suffix))
    if cloud_gangs:
        return max(cloud_gangs)

    # 2. Patrones de modelos y nombres (CB0x, TS000x, DS-10x, WS-10x, doble, triple, etc.)
    name = str(config.get("name") or "").lower()
    product = str(config.get("product_name") or "").lower()
    model = str(config.get("model") or "").lower()
    text = f"{name} {product} {model}".lower()

    import re
    # Check model codes: e.g. CB01..08, TS0001..0004, TS0011..0014, SW01..08, WF-WS01..08
    match = re.search(r"\b(?:cb0?|ts000|ts001|sw0?|wf[-_]?ws0?)([1-8])\b", text)
    if match:
        return int(match.group(1))

    match = re.search(r"\b(?:ds|ws|ms|ss|ts|ks)[-_]?(?:10|60)([1-8])\b", text)
    if match:
        return int(match.group(1))

    match = re.search(r"\b([1-8])\s*[-_]?\s*ch\b", text)
    if match:
        return int(match.group(1))

    # Explicit text patterns
    if any(w in text for w in ("triple", "3 gang", "3-gang", "3gang", "3 canal", "3 canales", "3 vías", "3 vias", "3 boton", "3 botones", "3 button", "3-button", "3 relay", "3-relay")):
        return 3
    if any(w in text for w in ("doble", "dual", "double", "2 gang", "2-gang", "2gang", "2 canal", "2 canales", "2 vías", "2 vias", "2 boton", "2 botones", "2 button", "2-button", "2 relay", "2-relay")):
        return 2
    if any(w in text for w in ("cuadruple", "cuádruple", "quad", "4 gang", "4-gang", "4gang", "4 canal", "4 canales", "4 vías", "4 vias", "4 boton", "4 botones", "4 button", "4-button", "4 relay", "4-relay")):
        return 4
    if any(w in text for w in ("simple", "single", "1 gang", "1-gang", "1gang", "1 canal", "1 vías", "1 vias", "1 boton", "1 botones", "1 button", "1-button", "1 relay", "1-relay", "unipolar")):
        return 1

    # 3. Detección por canales booleanos contiguos en LAN (1..N)
    disc_dps = config.get("discovered_dps") or {}
    init_dps = config.get("initial_dps") or {}
    dps_pool = {**init_dps, **disc_dps}
    if raw_dps and isinstance(raw_dps, dict):
        dps_pool.update(raw_dps)

    contiguous = 0
    for i in range(1, 9):
        val = dps_pool.get(str(i)) if str(i) in dps_pool else dps_pool.get(i)
        is_bool = False
        if isinstance(val, bool):
            is_bool = True
        elif isinstance(val, dict) and val.get("kind") == "boolean":
            is_bool = True
        if is_bool:
            contiguous = i
        else:
            break

    if contiguous > 0:
        return contiguous

    return 8


