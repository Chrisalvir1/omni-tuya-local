# Release v1.0.3 - Fix de Estabilidad de Conexión LAN y Prevención de Bloqueo de Sockets

Esta versión corrige de inmediato el problema de desconexión masiva (`unavailable`) en dispositivos locales introducido por el sondeo agresivo de versiones de protocolo en la v1.0.2.

## 🚀 Correcciones en v1.0.3

### 1. Eliminación de Sondeo Agresivo en el Bucle de Polling (`device.py`)
- **Protección de Sockets Tuya**: Los microcontroladores Tuya (ESP8266, Beken, Realtek) poseen pilas TCP limitadas que pueden colapsar o bloquearse si reciben tramas de versiones no coincidentes (ej. enviar paquetes `3.5` a un dispositivo `3.3`). Se eliminó el reintento agresivo de protocolo del sondeo rutinario para asegurar que cada dispositivo use de forma estable y directa su versión configurada (`3.3` o la establecida por el usuario).
- **Rendimiento Ultrarrápido**: Las consultas periódicas retornan de inmediato sin saturar los hilos de ejecución de Home Assistant.

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/device.py`
- `README.md`
- `RELEASE_NOTES_v1.0.3.md`
