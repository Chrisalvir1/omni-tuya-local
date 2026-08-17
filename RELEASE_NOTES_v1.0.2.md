# Release v1.0.2 - Iconos Dinámicos Nativos, Soporte Panel de Energía y Diagnósticos HA

Esta versión incluye mejoras clave de rendimiento, soporte nativo para el panel de energía de Home Assistant, autonegociación de protocolos LAN y soporte para la plataforma oficial de diagnósticos.

## 🚀 Mejoras en v1.0.2

### 1. Iconos Dinámicos Nativos de Home Assistant (`entity.py`)
- **Respeto a `device_class`**: La propiedad `icon` ahora respeta los iconos automáticos y adaptativos de Home Assistant según la clase y estado del sensor (nivel de batería, estado de puertas/ventanas, potencia eléctrica, temperatura, etc.), evitando sobreescribir los iconos con el del dispositivo principal.

### 2. Integración Nativa con el Panel de Energía (`sensor.py`)
- **Escalado Automático de Energía**: Las lecturas de consumo acumulado (DPS 17 / `add_ele`) se normalizan y escalan automáticamente en `kWh` con clase `TOTAL_INCREASING`, permitiendo agregar los dispositivos directamente al panel oficial de **Energía** de Home Assistant.

### 3. Autonegociación Rápida de Protocolos LAN (`device.py`)
- **Detección Automática de Cifrado (3.1 / 3.3 / 3.4 / 3.5)**: Manejo reactivo de errores de descifrado y framing (error 914) para negociar automáticamente entre versiones de protocolo LAN sin intervención manual del usuario.

### 4. Soporte Oficial de Diagnósticos de HA (`diagnostics.py`)
- **Descarga de Diagnósticos Nativa**: Se implementó `diagnostics.py` para permitir la descarga directa de un reporte estructurado de estado y DPS con claves privadas ofuscadas desde la tarjeta de la integración en Home Assistant.

---

## 🛠️ Archivos Modificados / Creados
- `custom_components/omni_tuya_local/manifest.json`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/entity.py`
- `custom_components/omni_tuya_local/sensor.py`
- `custom_components/omni_tuya_local/device.py`
- `custom_components/omni_tuya_local/diagnostics.py` [NUEVO]
- `README.md`
- `RELEASE_NOTES_v1.0.2.md`
