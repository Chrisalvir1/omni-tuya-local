# Omni Tuya Local v0.5.23

### Novedades y Correcciones
- **Mejora en Detección Dinámica de Dimmers**: Se corrigió el mapeo de DPS para interruptores dimmer (como ELEGRP). Anteriormente, la integración forzaba el DPS `3` como brillo por defecto, lo cual provocaba que en ciertos dimmers se modificara el *límite de atenuación mínimo* en lugar de la intensidad de la luz en tiempo real. Ahora la integración detecta si el DPS `2` transmite un valor numérico e inteligentemente lo asigna como el control primario de brillo (dimmer), respetando la estructura de las bombillas RGB estándar donde el DPS `2` es un modo de color.

**Archivos Modificados:**
- `custom_components/omni_tuya_local/light.py`
- `custom_components/omni_tuya_local/const.py`
- `custom_components/omni_tuya_local/manifest.json`
