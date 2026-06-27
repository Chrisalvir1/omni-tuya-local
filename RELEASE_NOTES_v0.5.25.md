# Omni Tuya Local — v0.5.25

## 🐛 Corrección de errores de credenciales Tuya Cloud

### Problema corregido
Las credenciales válidas de Tuya IoT Platform eran rechazadas silenciosamente sin mostrar el motivo real del error.

### Cambios

- **`cloud.py`**: Detecta respuestas de error de la API Tuya (`success: false`) y lanza una excepción con el código y mensaje exacto del error (ej: `code 1010: token invalid`, `code 2406: skill id invalid`). Antes, estos errores se ignoraban y se retornaba una lista vacía.

- **`config_flow.py`**: El error de autenticación ahora se registra en el log de Home Assistant con `_LOGGER.error(...)`. Se distingue entre *autenticación fallida* y *autenticación exitosa sin dispositivos con local_key* (`no_devices`).

- **`translations/es.json`**: Mensaje de error `cloud_error` mejorado con pasos específicos de verificación y referencia a los logs de HA.

### Cómo diagnosticar si persiste el error
1. Recarga la integración
2. Intenta agregar el dispositivo con tus credenciales
3. Ve a **Configuración → Sistema → Logs** y busca `"Tuya Cloud API error"`
4. El log mostrará el código exacto (ej: `code: 1010, msg: token invalid`)
