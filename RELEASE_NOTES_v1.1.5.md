# Release v1.1.5 — Soporte Nativo para Sensores Wi-Fi a Batería (Reposo Profundo y Eventos UDP)

Esta versión resuelve el estado "No disponible" en sensores Wi-Fi a batería (sensores magnéticos de puerta/ventana, sensores de movimiento PIR, sensores de fugas, etc.) que entran en reposo profundo (*Deep Sleep*) para ahorrar batería.

## 🚀 Mejoras y Correcciones en v1.1.5

### 1. Gestión de Disponibilidad para Dispositivos de Reposo Profundo (`device.py`)
- Los sensores que operan a batería (`door_sensor`, `window_sensor`, `motion_sensor`, `water_leak_sensor`, etc., o categorías `mcs`, `cs`, `pir`) ahora se reconocen como dispositivos en reposo (`is_sleep_device`).
- Cuando tienen una dirección IP asignada, se mantienen en estado **Disponible** (`available = True`). El fallo normal de conexión TCP cuando el sensor está durmiendo ya no marca la entidad como "No disponible".
- Sondeo optimizado y no bloqueante: para dispositivos en reposo se realiza una verificación rápida de 1 segundo en lugar de bloquear el hilo de sondeo por tiempos prolongados.

### 2. Captura y Actualización en Vivo por Broadcast UDP (`discovery.py` & `coordinator.py`)
- El listener UDP en los puertos 6666 y 6667 ahora extrae los Data Points (`dps`) directamente de los paquetes de broadcast que el sensor emite al despertar al abrir o cerrar la puerta.
- El coordinador procesa estos eventos de forma inmediata y actualiza el estado de la entidad en Home Assistant sin necesidad de esperar a un ciclo de sondeo.

### 3. Estado Inicial Seguro y Fallback de DPS (`binary_sensor.py`)
- Sensores de contacto de puerta/ventana recién agregados muestran un estado inicial limpio ("Cerrado") en lugar de quedar en estado no disponible o desconocido.
- Búsqueda de DPS alternativos estándar para sensores de contacto Tuya (`1`, `101`, `102`, `doorcontact_state`).

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/device.py`
- `custom_components/omni_tuya_local/discovery.py`
- `custom_components/omni_tuya_local/coordinator.py`
- `custom_components/omni_tuya_local/binary_sensor.py`
- `RELEASE_NOTES_v1.1.5.md`
