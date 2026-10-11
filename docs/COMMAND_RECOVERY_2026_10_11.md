# Omni Tuya Local — recuperación de comandos, 2026-10-11

## Diagnóstico confirmado

El log de Home Assistant compartido contiene un NameError de CONF_DEVICE_ID durante recuperación de IP, rechazos Tuya 904 y errores LAN 914/901. La inspección confirmó bloqueos distintos para polling y escrituras sobre el mismo cliente, éxito optimista ante timeout, publicación de snapshots antiguos y errores de comandos ignorados por las entidades. set_status y set_value producen el mismo CONTROL en TinyTuya; repetirlos no corrige estos rechazos.

## Correcciones

- device.py: bloqueo compartido asíncrono y bloqueo de workers; plazos compatibles con reintentos; errores explícitos; prioridad del DPS recibido; normalización de alias; pruebas de protocolo solo por lectura; actualización push en event loop.
- coordinator.py: constantes de recuperación IP; propagación HomeAssistantError para todos los comandos; publicación del caché actual; disponibilidad basada en respuesta LAN; cancelación de tareas y cierre fuera del event loop.
- registry.py e __init__.py: búsqueda de dispositivos limitada a la config entry, compatible con Core 2026.10.
- switch.py: lectura de booleanos y representaciones 0/1 y true/false.
- tests: regresiones de concurrencia, timeout, rechazo, DHCP, protocolo, caché, registro y servicios reales.

## Verificación

- Python 3.11.16: 70 pruebas unitarias y 16 subtests aprobados.
- Python 3.14.2: 70 pruebas unitarias y 16 subtests aprobados.
- Home Assistant Core 2026.10.0 / Python 3.14.2: 9 pruebas de integración aprobadas.
- Advertencia externa de aiohttp en Home Assistant; no fallo de la integración.

No se cambian claves locales, identificadores, entidades ni emparejamientos. Sin migración de almacenamiento ni despliegue en HA.

## Pendiente físico

Comprobar encendido/apagado desde HA y Apple Casa, cambio de IP y reinicio con los dispositivos del usuario. Un ACK vacío válido se acepta según TinyTuya y se verifica mediante lectura posterior; no garantiza una acción física. Si persiste 904, revisar clave local, protocolo, esquema DPS y acceso LAN con diagnósticos nuevos. Los tests simulados no confirman la reparación del hardware. No se afirma que todos los errores posibles del proyecto estén resueltos.

## Separación LAN y Cloud

Los comandos y lecturas de estado llaman TinyTuya Device en la IP local por TCP. La importación/sincronización Cloud sigue disponible cuando el usuario la inicia para recuperar ID, clave local, nombre y esquema. Quitamos la sincronización periódica y el intento automático al arrancar; no se requiere una API de nube para las órdenes cotidianas.

Además, al retirar o deshabilitar un dispositivo se cierra su listener/cliente LAN. Se quitaron asociaciones de descubrimiento que identificaban dispositivos por IP fija; ahora se requiere que el broadcast aporte su ID Tuya.

## Dependencias y versión

TinyTuya 1.20.0 coincide con la última versión estable observada en PyPI al 11-10-2026; se mantiene fijada. No hay un manifiesto de dependencias de desarrollo propio: las pruebas de integración obtienen pytest y utilidades del checkout oficial de Home Assistant Core. requests, cryptography y colorama son transitivas de TinyTuya/Core y no se fijan aparte para no pelear con las restricciones del entorno HA. Versión de esta entrega: 1.11.0.
