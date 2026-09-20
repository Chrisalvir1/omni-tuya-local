# Release v1.1.4 — Corrección de Extracción de Local Key para Dispositivos Tuya Cloud

Esta versión corrige un problema crítico que impedía agregar dispositivos mediante credenciales de Tuya Cloud cuando se ingresaban UIDs de usuario de Smart Life / Tuya IoT Platform.

## 🚀 Mejoras y Correcciones en v1.1.4

### 1. Extracción Robusta de `local_key` en Consultas Cloud (`cloud.py`)
- Se corrigió la discrepancia de nombres entre la API nativa de Tuya (`/v1.0/users/{uid}/devices`), que retorna la clave como `local_key`, y el normalizador de TinyTuya (`key`). Ahora se busca de forma segura en `local_key`, `key`, `localKey` y `localkey`.
- Se solucionó el error *"No se encontraron dispositivos con local key disponible"* que ocurría al sincronizar dispositivos vinculados a cuentas de Smart Life.

### 2. Soporte Ampliado para Múltiples UIDs y Virtual IDs (`cloud.py`)
- Soporte para ingresar múltiples IDs separados por comas (UIDs o Device IDs) en el campo de ID virtual.
- Consulta dinámica tanto para UIDs (`/v1.0/users/{uid}/devices`) como para Device IDs individuales (`/v1.0/devices/{device_id}`).
- Mecanismo de respaldo automático: si algún dispositivo devuelto en el listado omite su `local_key`, se consulta automáticamente el detalle individual (`/v1.0/devices/{id}`) para garantizar su recuperación.
- Se filtran UIDs y cadenas con comas para que no se pasen erróneamente como `apiDeviceID` al cliente de TinyTuya.

### 3. Cobertura de Pruebas Unitarias (`tests/test_cloud.py`)
- Se añadieron pruebas automatizadas cubriendo:
  - Formateo y extracción de `local_key` desde payloads nativos de Tuya OpenAPI.
  - Sincronización multi-UID con IDs separados por comas.
  - Recuperación de clave mediante fallback individual.
  - Normalización y búsqueda de dispositivos por dirección MAC.

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/cloud.py`
- `tests/test_cloud.py`
- `RELEASE_NOTES_v1.1.4.md`
