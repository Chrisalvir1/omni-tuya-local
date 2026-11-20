# Omni Tuya Local v1.12.6

20 de noviembre de 2026

- Añade la consulta de capacidad de altavoz a `omni_tuya_local/camera_webrtc` para Matter All-in-One 2.3.21. Requiere una conexión de administrador de Home Assistant y devuelve solo el indicador de retorno de voz.
- Admite conversación por turnos o simultánea si Tuya confirma la presencia de altavoz. Las credenciales de señalización y MQTT se solicitan al abrir la sesión de voz.
- Mantiene TinyTuya 1.21.1 y la corrección del mando «Alimentar ahora» de 1.12.5.

## Verificación

Pasaron 122 pruebas unitarias y dos pruebas del contrato WebSocket con Home Assistant Core 2026.11.2. Falta comprobar en Apple Casa que la voz llegue al altavoz físico del Comedero Michi.
