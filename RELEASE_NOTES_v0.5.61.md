# Release v0.5.61 - Soporte completo para Robots Aspiradores ROPVACNIC / Tuya (Categoría `sd`)

Esta versión incluye el soporte nativo, probado y definitivo para robots aspiradores ROPVACNIC y dispositivos Tuya pertenecientes al perfil estándar `sd` (Robot Vacuum).

## 🚀 Novedades y Mejoras

### 1. Mapeo Nativo de DPS (`sd`)
Se han estandarizado y nombrado todos los Data Points (DPS) del perfil `sd` de Tuya, aun en dispositivos agregados localmente sin esquema cloud:
- **DPS 2 (`power_go`)**: "Inicio de limpieza" — Control de encendido/apagado (`true`/`false`).
- **DPS 3 (`mode`)**: "Modo de limpieza" — Selección de modo (`standby`, `random`, `smart`, `wall_follow`, `spiral`, `chargego`).
- **DPS 4 (`direction_control`)**: "Control manual" — Mando direccional (`forward`, `backward`, `turn_left`, `turn_right`, `stop`).
- **DPS 5 (`status`)**: "Estado de limpieza" — Sensor de estado (`cleaning`, `goto_charge`, `charging`, `charge_done`).
- **DPS 6**: "Batería" — Nivel de batería (0–100 %). Expuesto en la entidad vacuum (`battery_level`) y como sensor de batería con icono y clase nativos.
- **DPS 7 / 8 / 9**: "Vida del cepillo lateral", "Vida del cepillo principal", "Vida del filtro" — Telemetría de mantenimiento en porcentaje.
- **DPS 17**: "Tiempo de limpieza" — Tiempo transcurrido en minutos.
- **DPS 18**: "Fallo del robot" — Registro/código de error.

### 2. Correcciones en la Entidad `vacuum`
- **Inicio y Detención Seguros**: `async_start` y `async_stop` ahora interactúan exclusivamente con el **DPS 2** (`power_go`), solucionando problemas donde la aspiradora permanecía inactiva al intentar enviar comandos al DPS 1.
- **Derivación de Estado Basada en DPS 5**:
  - `charge_done` y `charging` (así como `charge`, `dock`, `docked`) → `docked`.
  - `goto_charge` → `returning`.
  - `cleaning`, `smart_clean`, `wall_clean`, `spot_clean` → `cleaning`.
  - Fallback a DPS 3 (`chargego` → `returning`) y DPS 2 (`true` → `cleaning`).
- **Acción Volver a Base Limpia**: La llamada "Volver a base" envía únicamente **DPS 3 = `chargego`**. Se han eliminado todos los comandos especulativos hacia DPS 101/104.

### 3. Nuevas Entidades Select y Compatibilidad Matter / HomeKit
- **`select.<robot>_modo_de_limpieza`**: Expone los modos autónomos del robot en DPS 3. Si Tuya Cloud ofrece un rango personalizado de funciones en `tuya_functions`, la integración lo utiliza dinámicamente en lugar del fallback estándar.
- **`select.<robot>_control_manual`**: Expone el control direccional en DPS 4 (`forward`, `backward`, `turn_left`, `turn_right`, `stop`).
- **Separación Clara**: Control manual no se mezcla con el modo de limpieza; es un control direccional independiente.
- **Listas para Bridges**: Ambas entidades quedan perfectamente estructuradas como entidades `select` estándar de Home Assistant, facilitando su mapeo e integración a través de **HomeKit Bridge** o **Matter bridges** (ej. addon Matter All-in-One / integración Matter).

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/dps.py`
- `custom_components/omni_tuya_local/vacuum.py`
- `custom_components/omni_tuya_local/select.py`
- `custom_components/omni_tuya_local/sensor.py`
- `README.md`
- `RELEASE_NOTES_v0.5.61.md`
