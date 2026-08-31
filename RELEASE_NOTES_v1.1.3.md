# Release v1.1.3 — Compatibilidad con HA 2026.8 (Sensores de Batería) y Diagnóstico de Tuya Cloud

Esta versión resuelve las advertencias de deprecación de Home Assistant para entidades de aspiradora (`vacuum`), migrando el reporte de nivel de batería a entidades de sensor dedicadas, y mejora los diagnósticos de conexión con Tuya Cloud.

## 🚀 Mejoras en v1.1.3

### 1. Migración de Batería de Aspiradoras a Sensores Dedicados (`vacuum.py` & `sensor.py`)
- Se eliminó el feature deprecado `VacuumEntityFeature.BATTERY` y la propiedad `battery_level` de `OmniTuyaVacuum`, asegurando total compatibilidad a futuro con Home Assistant 2026.8+.
- Creación automática de la entidad `sensor.<aspiradora>_bateria` con `SensorDeviceClass.BATTERY`, unidad `%` y `state_class: measurement`, vinculada correctamente a la tarjeta del dispositivo.
- Soporte para fallbacks de búsqueda de DP de batería por código (`electricity_left`, `battery_percentage`, `battery`).

### 2. Diagnóstico Mejorado para Suspensión de Data Center en Tuya Cloud (`cloud.py`)
- Detección precisa del código de error `28841107` (*Data center is suspended*), con instrucciones claras en los registros indicando cómo renovar la suscripción de *IoT Core* o autorizar el Data Center en [Tuya IoT Platform](https://iot.tuya.com).

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/vacuum.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/cloud.py`
- `tests/test_sensor.py`
- `RELEASE_NOTES_v1.1.3.md`
