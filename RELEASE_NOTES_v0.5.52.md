# Omni Tuya Local 0.5.52

- Los comandos se envían por TCP local sin esperar un sondeo completo; la entidad se actualiza al instante y se verifica en segundo plano.
- Se validan las respuestas de error de TinyTuya para no informar comandos fallidos como exitosos.
- El sondeo lento ya no bloquea un comando de usuario.
- Desactiva la sincronización cloud automática; la nube queda solo para sincronizaciones manuales de credenciales y metadatos.
