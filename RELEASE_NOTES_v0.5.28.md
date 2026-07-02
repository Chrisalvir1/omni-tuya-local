# Release Notes v0.5.28

## Hotfix: Switches "Canal" fantasmas en Alarma Solar (alarm_kit)

### Problema corregido
- En la versión `0.5.27`, se eliminó el mapeo explícito de zonas 1-4 como switches, para que pasaran a ser `binary_sensor`. Sin embargo, esto causó que la lógica de la integración intentara "auto-detectar" cualquier DPS booleano sobrante y lo expusiera como un switch genérico (ej. "Canal 109", "Canal 102", etc.).
- **Solución:** Se ha bloqueado por completo la creación de switches automáticos para los dispositivos tipo `alarm_kit`. Ahora, los DPS de zonas y estado solo se crearán limpia y exclusivamente como **Sensores Binarios (binary_sensor)** de lectura, y el panel de alarma en sí mismo, sin switches confusos en la tarjeta principal.

### Archivos modificados
- `custom_components/omni_tuya_local/switch.py`
- `custom_components/omni_tuya_local/const.py`
