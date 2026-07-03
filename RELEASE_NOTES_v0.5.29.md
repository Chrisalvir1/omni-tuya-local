# Release Notes v0.5.29

## Hotfix: Sensores binarios faltantes en Alarma Solar

### Problema corregido
- En la versión `0.5.27`, creamos la lógica para exponer los sensores (movimiento PIR, zona activa, zonas 1-4) como `binary_sensor`. Sin embargo, el archivo `binary_sensor.py` tenía una condición antigua que descartaba cualquier dispositivo cuyo dominio principal no fuera `binary_sensor`. Como la alarma solar se clasifica bajo `alarm_control_panel`, el archivo `binary_sensor.py` lo ignoraba por completo y nunca llegaba a crear las entidades en Home Assistant.
- **Solución:** Se corrigió la condición en `binary_sensor.py` para permitir que cree sensores binarios cuando el `device_type` es `alarm_kit`, sin importar que su dominio principal sea `alarm_control_panel`. 

### Archivos modificados
- `custom_components/omni_tuya_local/binary_sensor.py`
- `custom_components/omni_tuya_local/const.py`
