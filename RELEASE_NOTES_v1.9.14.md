# Omni Tuya Local v1.9.14 Release Notes

## Corrección Definitiva: Purga Automática de Entidades Fantasma y Duplicadas en Apagadores e Interruptores de Pared (CB02, CB03, etc.)

### Problemas Solucionados
1. **Falla Silenciosa en Limpieza de Entidades**:
   - Se corrigió una incompatibilidad en el Device Registry de Home Assistant donde llamadas como `async_get_device_by_identifier` podían abortar la inicialización antes de que se ejecutara la rutina de limpieza.
   - Ahora el acceso a `device_registry` cuenta con fallback universal y tolerante a fallos para cualquier versión de Home Assistant.

2. **Purga Total de Entidades de Luz Fantasma en Apagadores de Pared**:
   - Se eliminan automáticamente del registro de entidades de Home Assistant (`entity_registry`) todas las entidades de luz espurias o marcadas como `(Oculta)` asociadas a apagadores físicos (`CB02-SBL`, `CB03-SBL`, `TS000x`, `Apagador Pasillo`, `Apagador Triple`, etc.).
   - Se previene que la plataforma `light.py` cree entidades de luz para controladores de pared.

3. **Purga Total de Sensores Fantasma / Huérfanos**:
   - Se eliminan automáticamente del registro de Home Assistant las entidades `DPS 2`, `DPS 3`, `DPS 16`, `Energía` y `Potencia` que aparecían como "No disponible" o "Desconocido" en apagadores físicos de pared.
   - Se previene que la plataforma `sensor.py` cree entidades de telemetría de energía o datos internos para interruptores que no cuentan con hardware de medición.

4. **Deduplicación Estricta de Canales de Switch**:
   - Cada botón físico cuenta exactamente con un único switch asociado (Canal 1..N).
   - Se eliminan canales duplicados (ej. `Canal 1` vs `PASILLO` o canales espurios como `Canal 16`).
   - Se añade una limpieza diferida en segundo plano para garantizar la purga incluso si las entidades ya estaban registradas al iniciar.
