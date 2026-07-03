# Release Notes v0.5.30

## Arquitectura: Soporte para Sensores de Movimiento Instantáneos (Push)

### Problema corregido
- Se detectó que el sensor de movimiento PIR (Alarma Solar `alarm_kit`) no actualizaba su estado en Home Assistant porque el dispositivo envía un evento (Push TCP) efímero que dura apenas **0.6 segundos** antes de regresar a la normalidad, lo cual hacía imposible capturarlo con el sistema tradicional de "polling" de la integración (que consulta el estado cada 5 segundos).

### Nuevas características
- **TCP Push Listener Dedicado:** Se ha implementado una nueva arquitectura de escucha en tiempo real. Para los dispositivos `alarm_kit`, la integración ahora mantiene abierta una conexión persistente en segundo plano (Daemon Thread) que escucha activamente todos los "gritos" (Pushes) del dispositivo sin bloquear Home Assistant.
- Cuando el dispositivo emite un evento instantáneo de movimiento, la interfaz de Home Assistant reacciona en milisegundos, actualizando el estado de la entidad sin tener que esperar al próximo ciclo de sondeo.
- **Sensor PIR Corregido:** Las pruebas en vivo revelaron que el dispositivo notifica el movimiento a través del **DPS 101** (pasando a `false` cuando hay movimiento), y no el DPS 106 como se deducía de otros esquemas de Tuya. Se ha actualizado el mapeo del Sensor Solar para reflejar esto correctamente.

### Archivos modificados
- `custom_components/omni_tuya_local/device.py`
- `custom_components/omni_tuya_local/coordinator.py`
- `custom_components/omni_tuya_local/binary_sensor.py`
- `custom_components/omni_tuya_local/const.py`
