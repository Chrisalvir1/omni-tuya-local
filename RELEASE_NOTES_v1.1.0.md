# Release v1.1.0 — Telemetría de Energía para HomeKit, Mejoras de HA y Suite de Pruebas

Esta versión incorpora la extracción completa y automática de sensores y telemetría de consumo de energía para todos los dispositivos Tuya, compatibilidad con accesorios de energía en Apple HomeKit (Eve Energy / Home+), mejoras en estándares de Home Assistant, pipeline de CI/CD automatizado y suite de pruebas unitarias.

## 🚀 Novedades y Mejoras en v1.1.0

### 1. Extracción Automática de Telemetría de Energía (`sensor.py`)
- Creación automática de entidades dedicadas e independientes de sensor para telemetría eléctrica:
  - **Potencia Activa (W)**: DPS `19` / `cur_power` (`SensorDeviceClass.POWER`, unidad `W`, `state_class: measurement`, escalado a `0.1 W`).
  - **Voltaje (V)**: DPS `20` / `cur_voltage` (`SensorDeviceClass.VOLTAGE`, unidad `V`, `state_class: measurement`, escalado a `0.1 V`).
  - **Corriente (mA)**: DPS `18` / `cur_current` (`SensorDeviceClass.CURRENT`, unidad `mA`, `state_class: measurement`).
  - **Energía Acumulada (kWh)**: DPS `17` / `add_ele` (`SensorDeviceClass.ENERGY`, unidad `kWh`, `state_class: total_increasing`).
- Detección inteligente a partir de telemetría local (`raw_dps`), esquema descubierto (`discovered_dps`) y funciones en la nube (`tuya_functions`).

### 2. Soporte HomeKit y Características Eve Energy (`switch.py`)
- Exposición de la propiedad `current_power_w` y atributos `current_power_w`, `voltage`, `current_a` y `total_energy_kwh` en los interruptores y tomacorrientes `OmniTuyaSwitch`.
- Permite que HomeKit Bridge y aplicaciones compatibles (como Eve for HomeKit, Home+ y Controller for HomeKit) muestren consumo de energía en vivo directamente sobre el accesorio.

### 3. Alineación con Estándares de Home Assistant
- **`text.py` y `button.py`**: Asignado `_attr_entity_category = EntityCategory.CONFIG` a la entidad de IP y botón de sincronización.
- **`climate.py`**: Soporte bidireccional en `async_set_temperature()` para termostatos Tuya que operan en décimas de grado (`val * 10` cuando raw `> 100`).
- **`fan.py`**: `async_set_percentage(0)` ahora apaga correctamente el ventilador con `async_turn_off()`.
- **`humidifier.py`**: Configuración de `HumidifierDeviceClass` y rangos `min_humidity = 30` / `max_humidity = 80`.
- **`__init__.py` y `coordinator.py`**: Cancelación de timers periódicos de sincronización al descargar la integración y optimización de imports.
- **`dps.py`**: Estandarización de nombres de DPS (`Potencia`, `Voltaje`, `Corriente`, `Energía`) y eliminación de bloque redundante.

### 4. CI/CD y Suite de Pruebas Unitarias
- **GitHub Actions (`.github/workflows/validate.yml`)**: Validación automática con Hassfest, HACS y ejecución de pruebas en Python 3.11, 3.12 y 3.13.
- **Suite de Pruebas Unitarias (`tests/`)**: 21 pruebas unitarias cubriendo modelos, perfiles DPS, energía, comederos de mascotas y utilidades.

---

## 🛠️ Archivos Modificados y Creados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/__init__.py`
- `custom_components/omni_tuya_local/coordinator.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/switch.py`
- `custom_components/omni_tuya_local/dps.py`
- `custom_components/omni_tuya_local/text.py`
- `custom_components/omni_tuya_local/button.py`
- `custom_components/omni_tuya_local/climate.py`
- `custom_components/omni_tuya_local/fan.py`
- `custom_components/omni_tuya_local/humidifier.py`
- `.github/workflows/validate.yml`
- `tests/`
- `README.md`
- `RELEASE_NOTES_v1.1.0.md`
