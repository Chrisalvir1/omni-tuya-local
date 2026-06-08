DOMAIN = "omni_tuya_local"
INTEGRATION_VERSION = "0.5.0"
BUILD_NUMBER = "20260607.7"

CONF_REGION = "region"
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_HOST = "host"
CONF_VERSION = "version"
CONF_DPS_MAP = "dps_map"
CONF_PRODUCT_NAME = "product_name"
CONF_DEVICE_TYPE = "device_type"
CONF_NODE_ID = "node_id"
CONF_GATEWAY_ID = "gateway_id"
CONF_GATEWAY_LOCAL_KEY = "gateway_local_key"
CONF_GATEWAY_HOST = "gateway_host"

DEFAULT_REGION = "us"
DEFAULT_VERSION = "3.3"
DEFAULT_POLL_INTERVAL = 30          # segundos — 15s era muy agresivo
DEFAULT_DISCOVERY_INTERVAL = 300    # segundos — escaneo periódico LAN
MAX_POLL_FAILURES = 5               # fallos antes de reducir frecuencia de poll
BACKOFF_POLL_INTERVAL = 120         # poll cada 2 min cuando el device falla

# ── DPS típicos Tuya (convenio de fábrica) ────────────────────────────────
DPS_SWITCH = "1"           # on/off principal
DPS_BRIGHTNESS = "3"       # brillo (10-1000)
DPS_COLOR_TEMP = "4"       # temperatura de color (0-255 o 0-1000)
DPS_HSV = "5"              # color HSV/hex
DPS_MODE = "2"             # modo de operación (scene, white, colour…)
DPS_TEMP_CURRENT = "3"     # temperatura actual (clima/sensor)
DPS_TEMP_TARGET = "4"      # temperatura objetivo (clima)
DPS_HVAC_MODE = "2"        # modo HVAC (heat/cool/auto)
DPS_FAN_SPEED = "3"        # velocidad ventilador
DPS_OSCILLATE = "8"        # oscilación
DPS_CURRENT_MA = "18"      # corriente mA (tomacorriente inteligente)
DPS_POWER_W = "19"         # potencia W
DPS_VOLTAGE_V = "20"       # voltaje V
DPS_COVER_POSITION = "3"   # posición cortina (0-100)

EXPORT_DOMAINS = [
    "switch",
    "light",
    "fan",
    "lock",
    "cover",
    "climate",
    "sensor",
    "binary_sensor",
    "button",
    "number",
    "select",
    "text",
    "vacuum",
    "alarm_control_panel",
    "humidifier",
]

PLATFORMS = [
    "switch",
    "light",
    "fan",
    "lock",
    "cover",
    "climate",
    "sensor",
    "binary_sensor",
    "button",
    "number",
    "select",
    "text",
    "vacuum",
    "alarm_control_panel",
    "humidifier",
]

DEVICE_TYPES = {
    "generic": {"label": "Generico", "icon": "mdi:devices"},
    "kitchen": {"label": "Cocina", "icon": "mdi:stove"},
    "coffee_maker": {"label": "Cafetera", "icon": "mdi:coffee-maker"},
    "kettle": {"label": "Hervidor", "icon": "mdi:kettle"},
    "rice_cooker": {"label": "Arrocera", "icon": "mdi:rice"},
    "air_fryer": {"label": "Freidora de aire", "icon": "mdi:pot-steam"},
    "microwave": {"label": "Microondas", "icon": "mdi:microwave"},
    "oven": {"label": "Horno", "icon": "mdi:toaster-oven"},
    "refrigerator": {"label": "Refrigerador", "icon": "mdi:fridge"},
    "washer": {"label": "Lavadora", "icon": "mdi:washing-machine"},
    "dryer": {"label": "Secadora", "icon": "mdi:tumble-dryer"},
    "dishwasher": {"label": "Lavaplatos", "icon": "mdi:dishwasher"},
    "fan": {"label": "Ventilador", "icon": "mdi:fan"},
    "air_conditioner": {"label": "Aire acondicionado", "icon": "mdi:air-conditioner"},
    "heater": {"label": "Calefactor", "icon": "mdi:radiator"},
    "humidifier": {"label": "Humidificador", "icon": "mdi:air-humidifier"},
    "dehumidifier": {"label": "Deshumidificador", "icon": "mdi:air-humidifier-off"},
    "air_purifier": {"label": "Purificador de aire", "icon": "mdi:air-purifier"},
    "robot_vacuum": {"label": "Robot aspirador", "icon": "mdi:robot-vacuum"},
    "vacuum": {"label": "Aspiradora", "icon": "mdi:vacuum"},
    "alarm_kit": {"label": "Kit de alarma", "icon": "mdi:shield-home"},
    "siren": {"label": "Sirena", "icon": "mdi:alarm-light"},
    "motion_sensor": {"label": "Sensor de movimiento", "icon": "mdi:motion-sensor"},
    "door_sensor": {"label": "Sensor de puerta", "icon": "mdi:door-open"},
    "window_sensor": {"label": "Sensor de ventana", "icon": "mdi:window-closed"},
    "smoke_sensor": {"label": "Sensor de humo", "icon": "mdi:smoke-detector"},
    "gas_sensor": {"label": "Sensor de gas", "icon": "mdi:gas-detector"},
    "co_sensor": {"label": "Sensor de monóxido de carbono (CO)", "icon": "mdi:detector"},
    "water_leak_sensor": {"label": "Sensor de fuga de agua", "icon": "mdi:water-alert"},
    "temperature_sensor": {"label": "Sensor temperatura", "icon": "mdi:thermometer"},
    "humidity_sensor": {"label": "Sensor humedad", "icon": "mdi:water-percent"},
    "presence_sensor": {"label": "Sensor presencia", "icon": "mdi:account-radar"},
    "illuminance_sensor": {"label": "Sensor de iluminancia (Lux)", "icon": "mdi:brightness-5"},
    "pm25_sensor": {"label": "Sensor de material particulado (PM2.5)", "icon": "mdi:air-filter"},
    "co2_sensor": {"label": "Sensor de CO2", "icon": "mdi:molecule-co2"},
    "vibration_sensor": {"label": "Sensor de vibración", "icon": "mdi:vibrate"},
    "tamper_sensor": {"label": "Sensor antisabotaje (Tamper)", "icon": "mdi:shield-alert"},
    "battery_sensor": {"label": "Sensor de batería baja", "icon": "mdi:battery-alert"},
    "lock": {"label": "Cerradura", "icon": "mdi:lock-smart"},
    "garage_door": {"label": "Porton/garaje", "icon": "mdi:garage"},
    "curtain": {"label": "Cortina", "icon": "mdi:curtains"},
    "blind": {"label": "Persiana", "icon": "mdi:blinds"},
    "light": {"label": "Luz", "icon": "mdi:lightbulb"},
    "dimmer": {"label": "Dimmer", "icon": "mdi:lightbulb-on"},
    "led_strip": {"label": "Tira LED", "icon": "mdi:led-strip-variant"},
    "outlet": {"label": "Tomacorriente", "icon": "mdi:power-socket-us"},
    "power_strip": {"label": "Regleta", "icon": "mdi:power-strip"},
    "switch": {"label": "Interruptor", "icon": "mdi:light-switch"},
    "ir_remote": {"label": "Control IR/RF", "icon": "mdi:remote"},
    "pet_feeder": {"label": "Comedero mascotas", "icon": "mdi:food-outline"},
    "water_fountain": {"label": "Fuente de agua", "icon": "mdi:fountain"},
    "sprinkler": {"label": "Riego", "icon": "mdi:sprinkler-variant"},
    "valve": {"label": "Valvula", "icon": "mdi:valve"},
    "pump": {"label": "Bomba", "icon": "mdi:pump"},
}

# ── Mapeo Tuya categoría → dominio HA (para guess_domain en models.py) ──────
TUYA_CATEGORY_TO_DOMAIN: dict[str, str] = {
    # Luces
    "dj": "light", "dd": "light", "fwd": "light", "dc": "light",
    "tgq": "light", "xktyd": "light",
    # Interruptores/tomas
    "tgkg": "switch", "kg": "switch", "cz": "switch", "pc": "switch",
    "tdq": "switch", "dlq": "switch",
    # Clima
    "kt": "climate", "wk": "climate", "qn": "climate",
    # Ventilador
    "fs": "fan", "fsd": "fan", "kj": "fan",  # kj=air purifier
    # Cortinas/persianas
    "cl": "cover", "clkg": "cover", "ckmkzq": "cover",
    # Cerraduras
    "ms": "lock", "videolock": "lock",
    # Sensores binarios
    "mcs": "binary_sensor", "cs": "binary_sensor",  # contacto
    "pir": "binary_sensor",    # movimiento
    "ywbj": "binary_sensor",   # humo
    "rqbj": "binary_sensor",   # gas
    "ldcg": "binary_sensor",   # presencia mmWave
    "sjcj": "binary_sensor",   # fuga de agua
    # Sensores numéricos
    "wsdcg": "sensor",  # temp+humedad
    "cgq": "sensor",    # luminancia
    "pm25": "sensor",   # PM2.5
    "co2bj": "sensor",  # CO2
    "sp": "sensor",     # panel solar / medidor energía
    "cwysj": "sensor",  # calidad agua
    # Robot aspirador
    "sd": "vacuum",
    # Alarma
    "ywj": "alarm_control_panel", "hjj": "alarm_control_panel",
    # Humidificador
    "jsq": "humidifier",
    # Número (setpoint, temporizador)
    "sfkzq": "number",  # dispensador
}

# ── HomeKit switch type hints (para entity_config del HomeKit Bridge) ────────
# Cuando el device_type es uno de estos, se sugiere este 'type' en HomeKit
HOMEKIT_SWITCH_TYPES: dict[str, str] = {
    "outlet": "outlet",
    "power_strip": "outlet",
    "sprinkler": "sprinkler",
    "valve": "valve",
    "water_fountain": "faucet",
    "pump": "valve",
}

HOMEKIT_FAN_TYPES: dict[str, str] = {
    "air_purifier": "air_purifier",
    "fan": "fan",
}

TUYA_BRIGHTNESS_MAX = 1000
TUYA_BRIGHTNESS_MIN = 10

TUYA_COLOR_TEMP_MIN = 0
TUYA_COLOR_TEMP_MAX = 1000

SERVICE_ADD_DEVICE = "add_device"
SERVICE_REMOVE_DEVICE = "remove_device"
SERVICE_SCAN_NETWORK = "scan_network"
SERVICE_SYNC_CLOUD = "sync_cloud"
SERVICE_SET_DEVICE_IP = "set_device_ip"
SERVICE_SET_DEVICE_DOMAIN = "set_device_domain"
SERVICE_SET_DEVICE_TYPE = "set_device_type"
SERVICE_RELOAD_DEVICES = "reload_devices"
SERVICE_DIAGNOSTICS = "diagnostics"
SERVICE_TEST_DEVICE = "test_device"
SERVICE_FETCH_DPS = "fetch_dps"

STORAGE_KEY = "omni_tuya_local.devices"
STORAGE_VERSION = 1
