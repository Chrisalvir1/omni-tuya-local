# Omni Tuya Local v0.4.1 — Hotfixes de Estabilidad (HA 2026.6.1)

Esta versión de mantenimiento corrige de forma inmediata errores críticos de inicialización reportados tras la migración a **Home Assistant 2026.6.1**.

## 🔧 Correcciones de Errores (Hotfixes)

### 1. Corrección en Plataforma de Iluminación (`light.py`)
* **Problema**: `ImportError: cannot import name 'ATTR_COLOR_TEMP' from 'homeassistant.components.light'`.
* **Solución**: Se actualizó por completo el archivo `light.py` para cumplir con las directivas del core de Home Assistant 2026.3+. Se eliminó el uso de la escala mireds y de las constantes deprecadas (como `ATTR_COLOR_TEMP`) en favor de la escala Kelvin nativa (`ATTR_COLOR_TEMP_KELVIN`, `min_color_temp_kelvin`, `max_color_temp_kelvin` y `color_temp_kelvin`). La integración ahora realiza internamente la conversión matemática de Kelvin a mireds para que la comunicación LAN local con tus bombillas siga funcionando perfectamente.

### 2. Corrección en Sensores Binarios (`binary_sensor.py`)
* **Problema**: `AttributeError: type object 'BinarySensorDeviceClass' has no attribute 'CARBON_MONOXIDE'`.
* **Solución**: Se corrigió la asignación del device class del sensor de monóxido de carbono (`co_sensor`) utilizando la constante correcta de Home Assistant: **`BinarySensorDeviceClass.CO`** (la cual mapea internamente al identificador de UI `"carbon_monoxide"`).

---

## 📦 Instalación y Actualización

1. Abre HACS en tu Home Assistant.
2. Busca la integración **Omni Tuya Local**.
3. Selecciona **Actualizar** a la versión **`v0.4.1`**.
4. Reinicia Home Assistant para aplicar los cambios de código.
