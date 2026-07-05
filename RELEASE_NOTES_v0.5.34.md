# Release Notes v0.5.34

## Hotfix Crítico: Fallo de Detección del Sensor Solar (DPS 106) y Cruce de Eventos Push

### Análisis Profundo del Problema
Tras una auditoría profunda a nivel de código de los eventos push TCP, se descubrieron dos problemas críticos adicionales que impedían por completo la detección de movimiento:

1. **Incompatibilidad de DPS (101 vs 106):** En una actualización anterior (v0.5.30), el ID del sensor de movimiento (DPS) para alarmas solares fue cambiado estrictamente a `101`. Sin embargo, algunos modelos de hardware de la alarma solar multizona emiten la detección de movimiento en el **DPS 106**. Al estar forzado a 101, la integración ignoraba por completo el movimiento real del dispositivo.
2. **Cruce de Eventos (Falsos Disparos Cruzados):** El parche anterior inyectaba una marca de tiempo (`_push_time`) global. Si el dispositivo actualizaba cualquier otra entidad (como el estado de Antisabotaje o una de las zonas), el código interpretaba erróneamente esa marca de tiempo como si el sensor solar hubiera recibido un evento. Como el estado en caché del sensor solar es siempre `False` (movimiento detectado) por ser efímero, **cualquier otra actualización hacía que el sensor de movimiento se disparara y reiniciara su temporizador (latch) en bucle**, manteniéndolo atascado internamente.

### Soluciones Implementadas
- **Soporte Simultáneo (DPS 101 y 106):** Se restauró el monitoreo del DPS `106` en el código, pero sin eliminar el `101`. Ahora verás un nuevo sensor llamado **"Sensor Solar (106)"**. Dependiendo de la versión exacta de hardware que poseas, uno de los dos sensores registrará perfectamente los eventos de movimiento (puedes ocultar el que no responda).
- **Aislamiento Estricto de Tiempos Push:** Se reescribió la lógica del *Push Listener* para aislar individualmente la marca de tiempo de cada DPS (`_push_time_101`, `_push_time_106`, etc.). Esto garantiza de manera absoluta que el sensor de movimiento de 3.5 segundos solo se dispare cuando el dispositivo envía explícitamente una señal para el DPS correcto, previniendo falsos positivos y garantizando el flujo a HomeKit.
