from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import TUYA_CATEGORY_TO_DOMAIN


@dataclass(slots=True)
class TuyaEntityDescription:
    entity_id_suffix: str
    platform: str
    dps_id: str = "1"
    semantic: str = "state"
    name: str | None = None
    device_class: str | None = None
    unit: str | None = None


@dataclass(slots=True)
class TuyaDeviceConfig:
    device_id: str
    name: str
    local_key: str
    host: str = ""
    version: str = "3.3"
    domain: str = "switch"
    product_name: str = ""
    product_id: str = ""
    category: str = ""
    device_type: str = "generic"
    area_id: str | None = None
    enabled: bool = True
    poll_interval: int = 30
    dps_map: dict[str, Any] = field(default_factory=dict)
    gateway_id: str = ""
    node_id: str = ""
    gateway_host: str = ""
    gateway_local_key: str = ""
    online: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    # Product-schema-derived pet-feeder controls and local serving preference.
    tuya_functions: list[dict[str, Any]] = field(default_factory=list)
    manual_feed_portions: int = 1
    pet_feeder_feed_dp: str = ""
    pet_feeder_feed_kind: str = ""
    pet_feeder_clean_hopper_dp: str = ""
    pet_feeder_clean_hopper_value: Any = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TuyaDeviceConfig":
        return cls(
            device_id=str(data.get("device_id") or data.get("id") or ""),
            name=str(data.get("name") or data.get("device_id") or "Tuya Device"),
            local_key=str(data.get("local_key") or data.get("key") or ""),
            host=str(data.get("host") or data.get("ip") or ""),
            version=str(data.get("version") or data.get("ver") or "3.3"),
            domain=str(data.get("domain") or guess_domain(data)),
            product_name=str(data.get("product_name") or ""),
            product_id=str(data.get("product_id") or ""),
            category=str(data.get("category") or ""),
            device_type=str(data.get("device_type") or guess_device_type(data)),
            area_id=data.get("area_id"),
            enabled=bool(data.get("enabled", True)),
            poll_interval=int(data.get("poll_interval") or 30),
            dps_map=dict(data.get("dps_map") or {}),
            gateway_id=str(data.get("gateway_id") or ""),
            node_id=str(data.get("node_id") or data.get("cid") or ""),
            gateway_host=str(data.get("gateway_host") or data.get("gateway_ip") or ""),
            gateway_local_key=str(data.get("gateway_local_key") or ""),
            online=data.get("online"),
            raw=dict(data.get("raw") or {}),
            tuya_functions=list(data.get("tuya_functions") or []),
            manual_feed_portions=max(1, int(data.get("manual_feed_portions") or 1)),
            pet_feeder_feed_dp=str(data.get("pet_feeder_feed_dp") or ""),
            pet_feeder_feed_kind=str(data.get("pet_feeder_feed_kind") or ""),
            pet_feeder_clean_hopper_dp=str(data.get("pet_feeder_clean_hopper_dp") or ""),
            pet_feeder_clean_hopper_value=data.get("pet_feeder_clean_hopper_value", True),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "local_key": self.local_key,
            "host": self.host,
            "ip": self.host,         # alias para compatibilidad
            "version": self.version,
            "domain": self.domain,
            "product_name": self.product_name,
            "product_id": self.product_id,
            "category": self.category,
            "device_type": self.device_type,
            "area_id": self.area_id,
            "enabled": self.enabled,
            "poll_interval": self.poll_interval,
            "dps_map": self.dps_map,
            "gateway_id": self.gateway_id,
            "node_id": self.node_id,
            "gateway_host": self.gateway_host,
            "gateway_local_key": self.gateway_local_key,
            "online": self.online,
            "raw": self.raw,
            "tuya_functions": self.tuya_functions,
            "manual_feed_portions": self.manual_feed_portions,
            "pet_feeder_feed_dp": self.pet_feeder_feed_dp,
            "pet_feeder_feed_kind": self.pet_feeder_feed_kind,
            "pet_feeder_clean_hopper_dp": self.pet_feeder_clean_hopper_dp,
            "pet_feeder_clean_hopper_value": self.pet_feeder_clean_hopper_value,
        }

    @property
    def has_host(self) -> bool:
        return bool(self.host and self.host.strip())

    @property
    def is_sub_device(self) -> bool:
        return bool(self.node_id and self.gateway_id)

    @property
    def effective_host(self) -> str:
        """IP real a usar para conectar (gateway si es sub-device)."""
        if self.is_sub_device:
            return self.gateway_host or self.host
        return self.host

    @property
    def local_key_masked(self) -> str:
        """Local key con los últimos 4 chars visibles para UI."""
        if len(self.local_key) >= 4:
            return f"{'*' * (len(self.local_key) - 4)}{self.local_key[-4:]}"
        return "****"


def guess_domain(data: dict[str, Any]) -> str:
    """Adivinar el dominio HA más apropiado para un dispositivo Tuya."""
    name = str(data.get("name") or "").lower()
    product = str(data.get("product_name") or "").lower()
    category = str(data.get("category") or "").lower()
    text = f"{name} {product}"

    # 1. Por categoría Tuya (fuente más confiable)
    if category and category in TUYA_CATEGORY_TO_DOMAIN:
        return TUYA_CATEGORY_TO_DOMAIN[category]

    # 2. Sensores binarios por categoría (que no están en el dict principal)
    if category in {"mcs", "cs", "pir", "ywbj", "rqbj", "ldcg", "sjcj"}:
        return "binary_sensor"

    # 3. Por nombre / product_name
    if any(w in text for w in ("light", "lamp", "bombillo", "luz", "dimmer", "led", "bulb", "luminaria")):
        return "light"
    if any(w in text for w in ("lock", "cerradura", "door lock", "smart lock")):
        return "lock"
    if any(w in text for w in ("climate", "thermostat", "termostato", "air conditioner", "aire acondicionado")):
        return "climate"
    if any(w in text for w in ("cover", "curtain", "shade", "cortina", "blind", "persiana", "roller")):
        return "cover"
    if any(w in text for w in ("vacuum", "aspirador", "robot vacuum", "sweeper")):
        return "vacuum"
    if any(w in text for w in ("fan", "ventilador", "purifier", "purificador")):
        return "fan"
    if any(w in text for w in ("motion", "movimiento", "door sensor", "contact", "smoke", "gas", "leak", "flood", "presence")):
        return "binary_sensor"
    if any(w in text for w in ("temperature", "humidity", "sensor", "temp", "humedad", "co2", "pm2.5", "illuminance")):
        return "sensor"
    if any(w in text for w in ("alarm", "alarma", "security system")):
        return "alarm_control_panel"
    if any(w in text for w in ("humidifier", "humidificador")):
        return "humidifier"
    return "switch"


def guess_device_type(data: dict[str, Any]) -> str:
    """Adivinar el tipo físico del dispositivo para icono y etiqueta."""
    name = str(data.get("name") or "").lower()
    product = str(data.get("product_name") or "").lower()
    category = str(data.get("category") or "").lower()
    text = f"{name} {product}"

    category_map: dict[str, str] = {
        "dj": "light", "dd": "dimmer", "fwd": "light", "dc": "light",
        "tgq": "switch", "tgkg": "switch", "kg": "switch",
        "cz": "outlet", "pc": "power_strip", "dlq": "switch", "tdq": "switch",
        "kt": "air_conditioner", "wk": "heater", "qn": "heater",
        "cl": "curtain", "clkg": "curtain", "ckmkzq": "curtain",
        "sd": "robot_vacuum", "fs": "fan", "fsd": "fan",
        "kj": "air_purifier",
        "ms": "lock", "videolock": "lock",
        "mcs": "door_sensor", "cs": "door_sensor",
        "pir": "motion_sensor",
        "wsdcg": "temperature_sensor",
        "ywbj": "smoke_sensor",
        "rqbj": "gas_sensor",
        "sjcj": "water_leak_sensor",
        "ldcg": "presence_sensor",
        "cgq": "illuminance_sensor",
        "pm25": "pm25_sensor",
        "co2bj": "co2_sensor",
        "jsq": "humidifier",
        "ywj": "alarm_kit", "hjj": "alarm_kit",
        "sfkzq": "pet_feeder",    # dispensador de alimento
        "cwwsq": "pet_feeder",    # comedero inteligente
        "cwysj": "water_fountain", # dispensador agua
        "sp": "outlet",           # smart plug / medidor
        "xktyd": "led_strip",     # tira LED
    }
    if category in category_map:
        return category_map[category]

    matches: dict[str, tuple[str, ...]] = {
        "coffee_maker": ("cafetera", "coffee maker", "coffee machine"),
        "rice_cooker": ("arrocera", "rice cooker"),
        "air_fryer": ("freidora", "air fryer"),
        "microwave": ("microondas", "microwave"),
        "oven": ("horno", "oven", "toaster"),
        "refrigerator": ("refrigerador", "fridge", "nevera"),
        "washer": ("lavadora", "washer", "washing machine"),
        "dryer": ("secadora", "dryer"),
        "dishwasher": ("lavaplatos", "dishwasher"),
        "robot_vacuum": ("robot vacuum", "aspirador robot", "sweeper robot"),
        "vacuum": ("vacuum", "aspiradora"),
        "alarm_kit": ("alarm", "alarma", "security kit"),
        "siren": ("siren", "sirena"),
        "air_conditioner": ("aire acondicionado", "air conditioner"),
        "fan": ("fan", "ventilador"),
        "air_purifier": ("purifier", "purificador", "air clean"),
        "heater": ("heater", "calefactor", "radiador"),
        "humidifier": ("humidifier", "humidificador"),
        "dehumidifier": ("dehumidifier", "deshumidificador"),
        "lock": ("lock", "cerradura"),
        "garage_door": ("garage", "garaje", "portón"),
        "curtain": ("curtain", "cortina", "roller"),
        "blind": ("blind", "persiana"),
        "led_strip": ("led strip", "tira led", "strip"),
        "light": ("light", "lamp", "luz", "bombillo", "bulb"),
        "dimmer": ("dimmer", "regulador"),
        "outlet": ("plug", "outlet", "socket", "tomacorriente", "enchufe"),
        "power_strip": ("power strip", "regleta"),
        "switch": ("switch", "interruptor", "apagador"),
        "motion_sensor": ("motion", "movimiento", "pir"),
        "door_sensor": ("door sensor", "contact", "magnetic"),
        "window_sensor": ("window sensor", "ventana", "window"),
        "smoke_sensor": ("smoke", "humo"),
        "gas_sensor": ("gas", "fuga de gas"),
        "co_sensor": ("co ", "carbon monoxide", "monóxido de carbono"),
        "water_leak_sensor": ("water leak", "fuga", "flood", "inundacion"),
        "presence_sensor": ("presence", "presencia", "mmwave", "radar"),
        "vibration_sensor": ("vibration", "vibración", "vibracion"),
        "tamper_sensor": ("tamper", "sabotaje", "antisabotaje"),
        "battery_sensor": ("battery low", "bateria baja", "batería baja"),
        "temperature_sensor": ("temperature", "temperatura", "thermometer"),
        "humidity_sensor": ("humidity", "humedad"),
        "kettle": ("kettle", "hervidor"),
        "sprinkler": ("sprinkler", "riego", "irrigation"),
        "valve": ("valve", "valvula"),
        "pump": ("pump", "bomba"),
        "ir_remote": ("remote", "control", "ir ", "rf ", "blaster"),
        "pet_feeder": ("feeder", "comedero", "mascota", "pet food", "alimentador"),
        "water_fountain": ("fountain", "fuente", "water dispenser"),
    }
    for device_type, words in matches.items():
        if any(word in text for word in words):
            return device_type
    return "generic"


def normalize_device(data: dict[str, Any]) -> dict[str, Any]:
    return TuyaDeviceConfig.from_dict(data).as_dict()
