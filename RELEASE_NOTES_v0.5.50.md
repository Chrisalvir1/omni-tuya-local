# Omni Tuya Local 0.5.50

- Evita que una pérdida breve de paquetes LAN marque inmediatamente un dispositivo como no disponible.
- Alinea los tiempos de espera de Home Assistant con los de TinyTuya y reintenta el estado local.
- Reescanea la LAN tras fallos persistentes para reparar IPs DHCP cambiadas.
- Cuando aparece el error 914, prueba una vez los protocolos Tuya compatibles y guarda el que responda.
