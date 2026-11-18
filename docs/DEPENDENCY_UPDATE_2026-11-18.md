# Actualización de dependencias — omni-tuya-local

Estado: cambios incorporados a la candidata v1.12.4, con publicación por GitHub Actions al crear el tag. Base: 6957fef8fa69177376b8656f98ee02a160ed6113

## Cambios

tinytuya1.21.1 en manifest y CI; Ruff0.17.5 y HAP-python5.2.0 en CI. Python3.14.10 y objetivo HA2026.11.2 con conservación de prueba2026.10.4. Smoke de imports aislado del contexto HomeAssistant incompleto que dejan otras pruebas, sin modificar lógica de entidades.

## Validación

Ruff correcto;120 pruebas unittest y18 pruebas Core con HA2026.11.2 correctas. No es un proyecto Node.

## Manifiestos modificados

| Archivo | Grupo | Dependencia | Antes | Ahora |
|---|---|---|---|---|

## Alcance

No se modificaron Chrisalvir Pro, Omni Broadlink, Fan BLE Home ni brands. No se actualizó el Node del host Camera.UI ni se modificaron instalaciones de producción. Los plugins requieren que su host cumpla Node>=26.13.1<27 antes de instalar esta actualización.
