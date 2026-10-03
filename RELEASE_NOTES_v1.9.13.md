# Omni Tuya Local v1.9.13 Release Notes

## Corrección de Botones Duplicados y Fantasma en Controladores Multi-Gang (CB03 / Apagadores Triples)

### Problema Resuelto
En interruptores y apagadores de pared físicos (como el **CB03-SBL** / **Apagador Triple**):
1. **Duplicación de Controles (Light vs Switch)**: Dispositivos de tipo interruptor configurados o detectados bajo múltiples plataformas generaban controles dobles (ej. `LUZ VENTILADOR BOTON (Oculta)` en luz y `BOTON VENTILADOR` en switch).
2. **Botones Falsos / No Físicos (Canal 16)**: El DPS 16 (correspondiente a la luz de fondo / backlight del switch físico o seguro infantil) era interpretado erróneamente como un canal de switch activo (`Canal 16`).
3. **Sensores Fantasma (DPS 2, DPS 3, DPS 7, Corriente, Potencia)**:
   - Los canales del switch (DPS 2 y 3) y temporizadores internos (DPS 7: cuenta regresiva de 0 segundos) eran expuestos como sensores.
   - Dispositivos de pared sin hardware de medición de energía creaban sensores de `Corriente` y `Potencia` que permanecían como "No disponible" o "Desconocido".

### Solución Implementada
- **Detección Automática de Canales Físicos (`max_gangs_for_device`)**:
  - Detección precisa de la cantidad real de canales según el modelo (CB01, CB02, CB03, CB04, etc.) o nombre ("Apagador Triple", "3 gang", etc.).
  - Para un CB03-SBL / Apagador Triple, restringe estrictamente a los **3 botones físicos reales** (Canal 1, 2 y 3), descartando por completo el DP 16.
- **Aislamiento de Plataformas**:
  - `switch.py` no creará switches si el dispositivo está configurado bajo otro dominio primario.
  - Se filtran códigos que no son canales de conmutación (ej. `switch_backlight`, `switch_led`, `switch_inching`).
- **Filtrado de Sensores en Interruptores**:
  - Se excluyen canales 1..8 y DPs de control interno (7..16, 21..26) de la plataforma de sensores.
  - Los sensores de energía (17..20) solo se crean en interruptores de pared si el dispositivo reporta valores de potencia activos mayores a 0.
- **Limpieza Automática en el Registro de Entidades (`async_cleanup_device_entities`)**:
  - Al iniciar Home Assistant o al recargar/cambiar configuración, se eliminan automáticamente del `entity_registry` las entidades duplicadas de luz, canales espurios (ej. `Canal 16`) y sensores no válidos.
