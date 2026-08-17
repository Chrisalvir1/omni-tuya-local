# Release v1.0.4 - Hotfix AttributeError en .icon y Deprecaciones de HA 2026

Esta versión corrige de forma definitiva el error crítico `AttributeError: object has no attribute '_attr_icon'` que impedía el registro de todas las entidades en Home Assistant, además de resolver advertencias de deprecación de HA 2026+.

## 🚀 Correcciones en v1.0.4

### 1. Fix Crítico: `AttributeError` en `.icon` (`entity.py`)
- Se corrigió el acceso a `_attr_icon` inicializándolo explícitamente en el constructor de `OmniTuyaEntity` y utilizando `getattr(self, "_attr_icon", None)`.
- Esto resuelve el fallo en `entity_platform.py` que impedía cargar las entidades de `vacuum`, `light`, `switch`, `sensor`, `binary_sensor`, `number`, `select` y `alarm_control_panel`.

### 2. Deprecaciones de Constantes de Concentración (`sensor.py`)
- Se sustituyeron las constantes obsoletas `CONCENTRATION_MICROGRAMS_PER_CUBIC_METER` y `CONCENTRATION_PARTS_PER_MILLION` por `UnitOfDensity.MICROGRAMS_PER_CUBIC_METER` y `UnitOfRatio.PARTS_PER_MILLION` con fallback retrocompatible.

### 3. Deprecación de Batería en `StateVacuumEntity` (`vacuum.py`)
- Se retiró la propiedad `battery_level` obsoleta y la bandera `VacuumEntityFeature.BATTERY` del objeto principal de la aspiradora, delegando el reporte del nivel de batería a la entidad dedicada de sensor de batería (`sensor.py` DPS 6) según las directrices de HA 2026+.

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/entity.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/vacuum.py`
- `README.md`
- `RELEASE_NOTES_v1.0.4.md`
