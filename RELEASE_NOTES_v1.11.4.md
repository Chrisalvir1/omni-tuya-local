# Omni Tuya Local v1.11.4

## Renovación del video Tuya para sesiones HAP

Matter All-in-One Chrisalvir puede solicitar a Omni una URL RTSP firmada nueva cada vez que HomeKit inicia una sesión Camera.UI/HAP. La solicitud usa un comando WebSocket autenticado de Home Assistant que solo acepta entidades de cámara registradas por Omni. El token HA no se reenvía al servidor RTSP de Tuya.

Después de reiniciar Home Assistant, la próxima apertura de video HAP vuelve a solicitar una asignación a Tuya, en vez de depender del trabajador de stream en caché de HA. Las URLs firmadas no se guardan ni se escriben en logs.

## Requisitos

- Actualiza Omni Tuya Local y Matter All-in-One Chrisalvir a versiones que incluyan este cambio coordinado.
- El proyecto Tuya necesita permiso **IoT Video Live Stream**, el firmware debe admitir la asignación RTSP y HA debe poder comunicarse con Tuya.
- Si Tuya o la red no responden, HomeKit no puede mostrar video en ese momento. La siguiente sesión vuelve a solicitar una asignación.
- Los sensores y controles DPS siguen usando la conexión LAN de Omni.

## Validación

Pruebas de unidad verifican la asignación RTSP, la entidad de cámara y la llamada HAP de renovación. La reproducción de video real depende del acceso activo al dispositivo y a la API Tuya.
