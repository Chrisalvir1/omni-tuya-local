## [Unreleased]

- Corregir la recuperación de IP que fallaba por constantes no importadas.
- Serializar lecturas y comandos LAN, incluso cuando un executor continúa después de un timeout.
- Propagar errores de comandos a Home Assistant; no declarar éxito ni cambiar el estado ante timeout o rechazo Tuya.
- Evitar publicaciones de estados antiguos, escrituras duplicadas y conflictos entre valores DPS numéricos y alias.
- Recuperar protocolos mediante lecturas independientes y cerrar clientes de prueba.
- Corregir búsquedas del registro de dispositivos para Core 2026.10 y cancelar tareas al descargar la integración.
- Añadir pruebas de regresión y de servicios reales con Core 2026.10.0.

## [1.10.0] - 2026-10-10

- Añadir una entidad `valve` nativa solo para dispositivos con clasificación y DPS de apertura/cierre explícitos; no se adivinan códigos de control.
- Añadir sensores de potencia reactiva/aparente, frecuencia y factor de potencia cuando el esquema Tuya y el dispositivo informan esos valores, con escalas declaradas y canales 1–4.
- Mantener el control cotidiano por LAN y la configuración persistente existente.
- Validar la plataforma Valve contra Home Assistant Core 2026.10.0 y Python 3.14.2.
