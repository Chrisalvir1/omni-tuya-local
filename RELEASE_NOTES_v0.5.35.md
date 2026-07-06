# Release Notes v0.5.35

## Bugfix Crítico: Lógica Inversa en Señal Efímera (Sensor Solar)

### Análisis Profundo del Problema
Gracias a la inspección de la tabla `raw_dps` del dispositivo en vivo, se descubrió la verdadera razón final por la cual el sensor solar se negaba a marcar "Detectado" en Home Assistant:

1. **El Mito del "False=Detectado":** El código original de la integración estaba programado asumiendo estrictamente que la alarma solar transmitía el valor lógico `False` cuando detectaba movimiento. Sin embargo, al inspeccionar el dispositivo en reposo, se confirmó que los DPS de movimiento (101 y 106) se mantienen en `False` cuando NO hay movimiento, lo que significa que el hardware envía un `True` al detectar a alguien (como es estándar en los sensores PIR).
2. **Ignorado por Diseño:** Debido a esta asunción errónea, cada vez que el dispositivo enviaba correctamente la señal `True` de detección, el código evaluaba internamente "Si no es False, ignóralo". Esto causaba que la integración fuera absolutamente ciega a los movimientos reales.

### Soluciones Implementadas
- **Agnosticismo de Estado en Pushes Efímeros:** Dado que la alarma solar solo emite eventos en la red local exactamente en el milisegundo en que se detecta movimiento (y no cuando está en reposo), se reescribió la lógica de intercepción. Ahora, **cualquier señal** recibida explícitamente en el canal 101 o 106 dispara instantáneamente la detección en Home Assistant por 3.5 segundos, sin importar si el fabricante envió un `True`, `False`, `1` o `0`. Esto garantiza 100% de fiabilidad en la captura del evento, previniendo falsos negativos por discrepancias booleanas en futuras versiones de hardware.
