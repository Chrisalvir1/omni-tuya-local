# Omni Tuya Local 0.5.55

- Corrige la recuperación del sensor solar de movimiento después de una pérdida de energía o Wi-Fi.
- El oyente TCP de eventos instantáneos ahora usa su propia conexión y se reconecta sin competir con el sondeo de estado.
- Si un dispositivo se cambia a `alarm_kit` desde los servicios de la integración, el oyente de movimiento se inicia sin requerir reiniciar Home Assistant.
