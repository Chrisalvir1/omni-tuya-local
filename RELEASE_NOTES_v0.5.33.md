# Release Notes v0.5.33

## Bugfix: Congelamiento de Estado del PIR Solar (DPS 101) y Compatibilidad con HomeKit

### Problemas corregidos
- Se solucionó un error donde el sensor de movimiento solar (DPS 101) se quedaba congelado en estado "Detectado" (`True`) en Home Assistant. Esto se debía a que los dispositivos de alarma Tuya envían el pulso efímero de movimiento (`False`) a través de un TCP Push, pero no emiten una señal de término (`True`), lo que causaba que la integración en cada ciclo de *polling* renovara el evento como si fuera nuevo.
- A causa del congelamiento, **HomeKit** y las **automatizaciones** dejaron de detectar nuevos eventos de movimiento, ya que el estado no retornaba a "No detectado" (es decir, faltaba la transición necesaria de estado para disparar la acción).

### Soluciones implementadas
- **Identificación de Pushes en Vivo:** La integración ahora estampa internamente el tiempo exacto en el que el dispositivo envía el pulso TCP en vivo (`_push_time`). Esto permite distinguir correctamente entre un nuevo evento de movimiento real y un simple reflejo de caché de estados viejos durante el *polling*.
- **Ajuste de Latch para HomeKit:** Se incorporó una transición automatizada donde el sensor se apaga a sí mismo después de haber sido activado. Adicionalmente, el retén artificial (*latch*) fue extendido a **3.5 segundos** (en lugar de 1 o 2.5 segundos), otorgando margen de sobra para que los *bridges* de HomeKit capten la señal de activación sin fallas y procesen la automatización, permitiendo de igual manera un reinicio rápido del sensor para la siguiente detección.
