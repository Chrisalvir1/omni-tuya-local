# Release v1.1.8 — Respaldo Cloud para Sensores a Batería

Omni Tuya Local conserva Tuya LAN como transporte primario. Cada 60 segundos
actualiza los datos Cloud únicamente para sensores a batería que entran en
reposo profundo, como contactos de puerta/ventana, PIR y fugas. Esto permite
reflejar el estado de modelos Wi-Fi que no exponen DPS por LAN, sin sustituir
los estados locales de interruptores, luces ni demás dispositivos LAN.
