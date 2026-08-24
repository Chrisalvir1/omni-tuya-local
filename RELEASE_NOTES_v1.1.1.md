# Release v1.1.1 — Robustez en Telemetría de Energía y Compatibilidad HomeKit (Eve Energy)

Esta versión perfecciona la detección, creación e inyección de datos de telemetría de energía eléctrica en Home Assistant y accesorios Apple HomeKit (Eve Energy / Home+), asegurando que tanto los dispositivos existentes como los futuros expongan sus métricas de inmediato.

## 🚀 Mejoras en v1.1.1

### 1. Pre-creación Inmediata de Sensores de Energía (`sensor.py`)
- Todos los dispositivos con capacidad de telemetría (enchufes inteligentes, regletas, relés, interruptores y medidores) generan automáticamente sus 4 entidades de sensor al iniciar Home Assistant, sin requerir esperar al ciclo de sondeo en red local:
  - **Potencia (W)**: `sensor.<dispositivo>_potencia` (`SensorDeviceClass.POWER`, unidad `W`, `state_class: measurement`)
  - **Voltaje (V)**: `sensor.<dispositivo>_voltaje` (`SensorDeviceClass.VOLTAGE`, unidad `V`, `state_class: measurement`)
  - **Corriente (mA)**: `sensor.<dispositivo>_corriente` (`SensorDeviceClass.CURRENT`, unidad `mA`, `state_class: measurement`)
  - **Energía Total (kWh)**: `sensor.<dispositivo>_energia` (`SensorDeviceClass.ENERGY`, unidad `kWh`, `state_class: total_increasing`)
- Compatible directamente con el **Panel de Energía de Home Assistant**.

### 2. Soporte Completo de Eve Energy en HomeKit (`switch.py` y `light.py`)
- Corrección en la evaluación de valores `0 W`, `0 V` y `0 A` para evitar que Python los descarte como valores nulos.
- Inyección garantizada de los atributos `current_power_w`, `voltage`, `current_a`, `current_ma` y `total_energy_kwh` en entidades `switch` y `light` (dimmers con medición).
- Permite que aplicaciones de HomeKit como **Eve for HomeKit**, **Home+** y **Controller for HomeKit** muestren gráficos y consumo en tiempo real.

### 3. Coordinador Resiliente (`coordinator.py`)
- `dps_value` ahora resuelve claves en formato cadena o entero (`"19"` o `19`) y consulta la caché local en memoria del dispositivo en caso de no haber completado el ciclo de actualización.

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/coordinator.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/switch.py`
- `custom_components/omni_tuya_local/light.py`
- `README.md`
- `RELEASE_NOTES_v1.1.1.md`
