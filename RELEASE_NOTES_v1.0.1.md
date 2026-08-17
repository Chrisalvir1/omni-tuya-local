# Release v1.0.1 - Soporte Multicanal Completo para Luces y Plugs (Fix Doble Canal en Home Assistant)

Esta versión soluciona de forma definitiva el problema donde la segunda toma o canal (DPS 2) de dispositivos dobles o multicanal no aparecía como control independiente o se creaba erróneamente como sensor binario cuando el dominio o tipo del dispositivo se asociaba a luces o interruptores.

## 🚀 Correcciones y Mejoras en v1.0.1

### 1. Soporte Multicanal en `light.py`
- **Descubrimiento y Creación Dinámica de Canales**: `light.py` ahora descubre y crea entidades de luz independientes para todos los canales activos (DPS 1, 2, 3...) en lugar de limitarse únicamente al DPS 1.
- **Acciones y Estado por Canal**: `is_on`, `async_turn_on` y `async_turn_off` ahora operan dinámicamente sobre el `dps_id` específico de cada canal de luz.

### 2. Bloqueo de Sensores Binarios Fantasma (`binary_sensor.py`)
- **Exclusión Completa de Canales de Control**: Se garantiza que ningún canal de switch o de luz (DPS 1..8) sea creado como un sensor binario de solo lectura en dispositivos de control (`switch`, `light`, `fan`, etc.).

### 3. Detección Inteligente de Tipo y Dominio (`models.py`)
- **Prioridad de Detección de Plugs/Outlets**: Se asegura que dispositivos como el "Smart Plug Duo (30220)" u otros plugs/regletas sean reconocidos como `switch` / `outlet` incluso si el usuario los nombra "Spot" o "Luz".

### 4. Perfiles de Sensores y Temporizadores (`sensor.py` y `dps.py`)
- **Desacoplamiento de Perfiles**: Los perfiles de porcentaje de aspiradora (`sd`) ya no contaminan el DP 9 y DP 10 de enchufes y regletas (donde representan temporizadores de cuenta regresiva).
- **Etiquetado Amigable**: Etiquetas estándar añadidas para canales de luz ("Luz 1", "Luz 2"...) y tomas ("Toma 1", "Toma 2"...).

---

## 🛠️ Archivos Modificados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/light.py`
- `custom_components/omni_tuya_local/binary_sensor.py`
- `custom_components/omni_tuya_local/models.py`
- `custom_components/omni_tuya_local/dps.py`
- `custom_components/omni_tuya_local/sensor.py`
- `README.md`
- `RELEASE_NOTES_v1.0.1.md`
