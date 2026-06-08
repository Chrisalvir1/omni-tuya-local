# Omni Tuya Local v0.4.3 — Auto-corrección de Versión del Protocolo

Esta versión corrige un problema crítico de desalineación en las versiones de protocolo (ej. usar versión `3.3` en dispositivos que anuncian y requieren `3.4` o `3.5` para descifrar la comunicación LAN local).

## 🚀 Mejoras y Correcciones de Estabilidad

* **Auto-corrección Dinámica de Versión (Hot-patching)**: El receptor de broadcasts UDP en segundo plano de la integración ahora verifica activamente la versión de protocolo que emite el hardware de forma local. Si el dispositivo está configurado con una versión diferente en la base de datos (por ejemplo, por descarte inicial a `3.3`), la integración actualizará automáticamente la versión a la correspondiente (`3.4` o `3.5`) y recargará la entidad de inmediato.
* **Fix en la Reconstrucción del Cliente Local**: Corregimos un bug en `device.py` donde cambiar la versión de protocolo o la `local_key` de un dispositivo no invalidaba la conexión TCP cacheada. Esto hacía que el dispositivo siguiera intentando dialogar usando el protocolo y comandos anteriores. Ahora, ante cualquier cambio de IP, versión o key, el cliente se reconstruye y aplica de forma instantánea.

---

## 📦 Instalación y Actualización

1. Abre HACS en tu Home Assistant.
2. Actualiza la integración **Omni Tuya Local** a la versión **`v0.4.3`**.
3. **Reinicia Home Assistant** para cargar los nuevos módulos de auto-corrección. El sistema detectará las versiones y restaurará tus entidades del apagador y demás dispositivos en el próximo ciclo de broadcast UDP.
