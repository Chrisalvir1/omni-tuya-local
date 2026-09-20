# Release v1.1.6 — Detección Automática de Sensores de Puerta/Ventana y Eliminación de Estado Desconocido

Esta versión resuelve de manera definitiva el problema por el cual los sensores magnéticos de puerta y ventana Wi-Fi a batería (como `WiFi门磁`, `SENSOR PUERTA DE OFICINA`) se clasificaban erróneamente como entidades numéricas de tipo `sensor` en estado "Desconocido", asegurando que se reconozcan como `binary_sensor` (puerta) con estados nativos **Cerrado** y **Abierto**.

## 🚀 Mejoras y Correcciones en v1.1.6

### 1. Detección Inteligente Multilingüe (`models.py`)
- Reconocimiento automático de sensores de contacto magnético en español, inglés y nombres de fábrica en chino:
  - Palabras clave: `puerta`, `door`, `portón`, `porton`, `ventana`, `window`, `contact`, `contacto`, `apertura`, `magnetic`, `magnético`, `magnetico`, `门`, `门磁`, `窗`, etc.
- Priorización antes del clasificador genérico de palabras (evita que `"SENSOR PUERTA..."` se clasifique como sensor numérico por contener la palabra `"sensor"`).
- Clasificación nativa como `domain: "binary_sensor"` y `device_type: "door_sensor"` (o `"window_sensor"`).

### 2. Auto-Sanitización de Dispositivos Existentes (`models.py` & `coordinator.py`)
- Al iniciar o recargar Home Assistant, cualquier sensor de puerta/ventana que hubiera quedado registrado con `domain: "sensor"` o `device_type: "generic"` se migra y corrige automáticamente a `binary_sensor` y `door_sensor`.
- Se evita que la plataforma `sensor.py` genere entidades numéricas ficticias `dps: 1` para sensores de puerta.

### 3. Estados Nativos "Cerrado" / "Abierto" (`binary_sensor.py`)
- Si el sensor aún no ha enviado eventos tras iniciar Home Assistant (al estar en reposo profundo), `OmniTuyaBinarySensor` asume de forma segura su estado físico de reposo (**Cerrado** / `False`) en lugar de `None` (**Desconocido**).
- Soporte para todas las variantes de DPS Tuya: `1`, `101`, `102`, `103`, `doorcontact_state`, `is_open`, `contact`.
- Mapeo de valores booleanos (`True`/`False`), texto (`open`, `close`, `closed`, `opened`, `standby`, `alarm`) y enteros (`1`/`0`).

### 4. Sondeo Inmediato al Despertar por Broadcast UDP (`coordinator.py` & `discovery.py`)
- Listener UDP ampliado a los puertos 6666, 6667 y 7000.
- Decodificación dual (TinyTuya descifrado + JSON plano).
- En cuanto el sensor despierta físicamente al abrir/cerrar la puerta y emite su anuncio UDP en la red local, el coordinador lanza una consulta instantánea TCP para leer su estado exacto antes de que vuelva al reposo profundo.

### 5. Estado Inicial desde Tuya Cloud (`cloud.py` & `device.py`)
- Al importar o sincronizar desde Tuya Cloud, el arreglo de `status` del endpoint OpenAPI (`doorcontact_state`) se guarda como `initial_dps` para que el sensor tenga su estado real desde el primer instante.
