# Release Notes v0.5.27

## Alarma Solar Tuya — Integración Correcta (Solar Driveway Alarm)

### Problemas corregidos

- **Zonas en gris (no interactivas)**: Los switches de Zona 1-4 (DPS 109-112) eran controles de escritura que el dispositivo no aceptaba. Ahora se exponen como `binary_sensor` read-only, reflejando correctamente el estado del selector físico de zona.

- **Sensor solar PIR no visible**: El sensor de movimiento solar separado (DPS 106) ahora aparece en HA como `binary_sensor` con `device_class: motion`, permitiendo crear automatizaciones basadas en detección de movimiento.

- **Categoría `mal` no reconocida**: La categoría Tuya `mal` (alarma solar de camino, `智能太阳能车道报警器`) ahora está mapeada correctamente a `alarm_control_panel` / `alarm_kit`. El dispositivo ya no requiere detección por nombre.

- **Trigger efímero del PIR**: El poll interval se reduce automáticamente a **5 segundos** cuando hay un `alarm_kit` activo, aumentando significativamente la probabilidad de capturar el trigger momentáneo del sensor solar (DPS 106).

### Nuevas entidades para alarm_kit

| Entidad | DPS | Device Class |
|---------|-----|-------------|
| Sensor Solar | 106 | `motion` |
| Zona Activa | 102 | `safety` |
| Zona 1 | 109 | `safety` |
| Zona 2 | 110 | `safety` |
| Zona 3 | 111 | `safety` |
| Zona 4 | 112 | `safety` |
| Antisabotaje | 119 | `tamper` |

### Archivos modificados
- `custom_components/omni_tuya_local/binary_sensor.py`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/coordinator.py`
- `custom_components/omni_tuya_local/models.py`
- `custom_components/omni_tuya_local/switch.py`
