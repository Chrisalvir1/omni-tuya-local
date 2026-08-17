# Release v1.0.0 - Soporte Completo para Plugs Dobles, Regletas Multicanal y Telemetría de Energía

Esta versión mayor (`v1.0.0`) introduce soporte integral para enchufes inteligentes Tuya de doble toma (dual smart plugs), regletas multicanal, interruptores de múltiples tomas/canales y telemetría de monitoreo de consumo eléctrico.

## 🚀 Novedades y Mejoras

### 1. Detección y Creación Multicanal de Switches (`switch.py`)
- **Descubrimiento Consolidado**: Ahora `_switch_dps` combina de forma inteligente todas las fuentes disponibles:
  - Definiciones de funciones de Tuya Cloud (`tuya_functions` como `switch_1`, `switch_2`, `switch_usb`, etc.).
  - Esquema persistido de DPS locales (`discovered_dps`).
  - Sondeo y eventos push en tiempo real en la red local (`raw_dps`).
  - Mapeo manual del usuario (`dps_map`).
- **Control Independiente**: Cada toma o canal recibe su propia entidad switch con Unique ID independiente (`omni_tuya_local_<id>`, `omni_tuya_local_<id>_2`, etc.).
- **Etiquetado Limpio**: Para dispositivos de múltiples tomas asigna automáticamente nombres descriptivos ("Toma 1", "Toma 2" o nombres personalizados de la nube), mientras que para dispositivos de una sola toma mantiene el nombre del dispositivo limpio en Home Assistant.

### 2. Corrección en `binary_sensor.py`
- **Exclusión de Canales de Switch**: Se solucionó el problema por el cual los canales secundarios (DPS 2, 3, 4...) de un enchufe o interruptor eran creados erróneamente como sensores binarios de solo lectura. Ahora todos los canales de switch se excluyen correctamente de la plataforma `binary_sensor`.

### 3. Telemetría de Monitoreo de Consumo Eléctrico (`sensor.py` y `dps.py`)
- **Perfiles Nativos de Medición**:
  - **DPS 18**: "Corriente" (`mA`) — `SensorDeviceClass.CURRENT`.
  - **DPS 19**: "Potencia" (`W`) — `SensorDeviceClass.POWER` (con conversión automática de décimas de W).
  - **DPS 20**: "Voltaje" (`V`) — `SensorDeviceClass.VOLTAGE` (con conversión automática de décimas de V).
  - **DPS 17**: "Energía" (`kWh`) — `SensorDeviceClass.ENERGY` (con clase de estado `TOTAL_INCREASING`).
- **Nombres y Clases Estándar**: Los sensores de consumo se crean con nombres e iconos adecuados y se integran automáticamente en el panel de energía de Home Assistant y HomeKit Bridge.

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/switch.py`
- `custom_components/omni_tuya_local/binary_sensor.py`
- `custom_components/omni_tuya_local/dps.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/models.py`
- `README.md`
- `RELEASE_NOTES_v1.0.0.md`
