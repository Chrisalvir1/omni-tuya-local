# Release Notes v0.5.32

## Tweak: Ajuste en el Retardo del Sensor de Movimiento (Latch)

### Ajustes implementados
- A petición, se redujo el "latch" artificial del Sensor Solar (DPS 101) de **5 segundos a 1 segundo**.
- El estado cambiará a "Detectado" instantáneamente, y ahora volverá a "No detectado" rápidamente después de 1 segundo para evitar mostrar falsos positivos de movimiento prolongado en la interfaz de Home Assistant. Esto es suficiente para que la UI parpadee visiblemente sin quedarse "pegada" demasiado tiempo.
