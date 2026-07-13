# Omni Tuya Local 0.5.54

- Corrige el estado visual tras encender o apagar: Home Assistant ya no asume que el comando se ejecutó.
- Después de cada comando LAN, consulta únicamente el dispositivo afectado y publica el estado solo con DPS recién recibido.
- Evita que un valor optimista o un sondeo de otro dispositivo deje una luz mostrada como encendida cuando está apagada.
