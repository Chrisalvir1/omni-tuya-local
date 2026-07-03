# Release Notes v0.5.31

## Hotfix: Visualización UI para Triggers Efímeros

### Problema corregido
- En la versión `0.5.30` se logró atrapar exitosamente el evento de movimiento del Sensor Solar en tiempo real. Sin embargo, como el evento físico dura apenas 0.6 segundos, la tarjeta de la interfaz de Home Assistant ("Sensores") no lograba reflejar el estado "Detectado" el tiempo suficiente para que el ojo humano lo notara (aunque en el "Historial / Registro" sí quedaba guardado perfectamente).

### Solución implementada
- **Retardo Artificial (Latch):** Se ha agregado un retén visual en el componente del `binary_sensor` (DPS 101). Cuando se detecta movimiento, el sensor forzará el estado "Detectado" durante al menos **5 segundos** antes de permitir que vuelva a "No detectado".
- Esto garantiza que Home Assistant pinte la interfaz gráfica correctamente y que las automatizaciones tengan tiempo de sobra para activarse con el evento de movimiento, mientras seguimos capturando el trigger en milisegundos gracias al Push Listener.
