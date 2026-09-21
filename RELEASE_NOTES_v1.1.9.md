# Release v1.1.9 — Mapeo Oficial de DPs de Puerta, Telemetría de Batería y Tamper

Esta versión implementa la extracción y el mapeo completo de Data Points (DPs) desde la especificación oficial de Tuya para sensores magnéticos de puerta y ventana Wi-Fi a batería (ej. `WiFi门磁`, `SENSOR PUERTA DE OFICINA`, `Steren SHOME-142`), resolviendo definitivamente el estado "Desconocido" y habilitando la entidad de **Batería** (`battery_percentage`) y **Antisabotaje** (`tamper_alarm`).

---

## 🚀 Mejoras y Correcciones en v1.1.9

### 1. Mapeo Oficial de Data Points (DPs) Tuya
- **DP 1 (`doorcontact_state`)**:
  - Plataforma: `binary_sensor`
  - Clase: `door` (o `window`)
  - Estados: `True` = Abierto, `False` = Cerrado (reposo físico).
  - Resuelve el estado "Desconocido" en Home Assistant inicializando en **Cerrado** o en el último valor registrado.
- **DP 2 (`battery_percentage`)**:
  - Plataforma: `sensor`
  - Clase: `battery`
  - Unidad: `%`
  - Generación automática de entidad para todos los sensores de puerta, ventana y categorías de seguridad (`mcs`, `cs`, `door_sensor`, `window_sensor`).
  - Resolución inteligente de fallback: consulta el estado local, `initial_dps`, o sincroniza el valor registrado por la integración Tuya en Home Assistant mientras el sensor está en reposo profundo.
- **DP 4 (`temper_alarm`)**:
  - Plataforma: `binary_sensor`
  - Clase: `tamper`
  - Estados: `False` = Normal / No detectado, `True` = Sabotaje detectado.

### 2. Soporte y Persistencia de `initial_dps` (`models.py` & `storage.py`)
- Se añade el campo `initial_dps` en `TuyaDeviceConfig` y se preserva en el almacenamiento local `.storage/omni_tuya_local.devices`.
- Se mapean automáticamente los códigos de OpenAPI (`doorcontact_state` → `1`, `battery_percentage` → `2`, `temper_alarm` → `4`) para que las entidades tengan su estado real de inmediato tras reiniciar Home Assistant sin esperar a que el sensor despierte físicamente.

### 3. Ajuste de Timeout y Manejo de Despertar UDP (`coordinator.py`)
- Se ajustó el timeout de consulta de 2.0s a 8.0s en `_async_poll_woken_device` para garantizar que la respuesta del sensor no sea descartada prematuramente cuando despierta al abrir o cerrar la puerta.

---

## 🧪 Pruebas Automatizadas
- 35 pruebas unitarias cubriendo clasificación de dispositivos, detección multilingüe, sanitización de esquemas, entidades binarias y cálculo de batería.
