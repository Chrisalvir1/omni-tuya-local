# Omni Tuya Local v1.9.19 Release Notes

## Correcciones para Enchufes Inteligentes (Plugs) y Control de Estado Inmediato

### Problemas Solucionados
1. **Fallback `updatedps` en Enchufes / Tomacorrientes**:
   - Muchos enchufes Tuya modernos (firmware LAN 3.3/3.4) no responden a la consulta genérica de estado `DP_QUERY` (código 10), provocando que Home Assistant muestre el estado como "Desconocido".
   - Se añadió fallback automático mediante `updatedps([1, 2, 9, 17, 18, 19, 20])` (código 18) en `device.py` para consultar y poblar los DPS reales del dispositivo de inmediato.

2. **Actualización de Estado Optimista al Enviar Comandos**:
   - Al pulsar encender o apagar en Home Assistant, el estado interno se actualiza de inmediato y se publica al coordinador. Esto evita que los botones queden congelados en "Desconocido" o no respondan a las pulsaciones en la interfaz.

3. **Auto-sondeo de Protocolo LAN**:
   - Se reactivó el sondeo automático seguro de protocolo LAN (3.3 / 3.4 / 3.1) cuando el dispositivo reporta errores de trama o cifrado (`904`, `914`, `Unexpected Payload`).

4. **Protección de Sensores en Enchufes y Tomacorrientes**:
   - Se corrigió el filtro de limpieza en `__init__.py` para que los enchufes, regletas y tomacorrientes (`outlet`, `plug`, `cz`, `sp`) no sean tratados como interruptores de pared físicos, asegurando que se preserven todos sus sensores de energía, potencia, corriente y voltaje.

5. **Corrección de `NameError` en `_mark_failure`**:
   - Se corrigió la variable `detail` en `device.py` y se aseguró el incremento correcto de fallos consecutivos antes de marcar un dispositivo como no disponible.
