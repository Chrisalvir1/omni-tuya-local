## [1.11.1] - 2026-10-11

- Corregir la sincronización de nombres y metadatos al volver a vincular dispositivos Tuya existentes.
- Actualizar credenciales y el identificador LAN actual al detectar la misma MAC, conservando la identidad estable del dispositivo y entidades de Home Assistant.
- Recargar dispositivos y títulos de configuración después de importar o sincronizar cambios desde Smart Life/Tuya Cloud.
- Añadir pruebas de regresión para renombrado y reemparejamiento por identidad física, sin sustituir el ID estable de Home Assistant.

## [1.11.0] - 2026-10-11

- Corregir la recuperación de IP que fallaba por constantes no importadas.
- Serializar lecturas y comandos LAN, incluso cuando un executor continúa después de un timeout.
- Propagar errores de comandos a Home Assistant; no declarar éxito ni cambiar el estado ante timeout o rechazo Tuya.
- Evitar publicaciones de estados antiguos, escrituras duplicadas y conflictos entre valores DPS numéricos y alias.
- Recuperar protocolos mediante lecturas independientes y cerrar clientes de prueba.
- Corregir búsquedas del registro de dispositivos para Core 2026.10 y cancelar tareas al descargar la integración.
- Añadir pruebas de regresión y de servicios reales con Core 2026.10.0.
- Mantener la importación manual desde Tuya Cloud, desactivar consultas automáticas cada 60 segundos y documentar que comandos/estados/DPS usan LAN.
- Cerrar los clientes LAN al retirar dispositivos y eliminar asociaciones de descubrimiento con IPs fijas.
- Confirmar que TinyTuya 1.20.0 ya es la última versión estable disponible; no se cambia la dependencia runtime.

## [1.10.0] - 2026-10-10

- Añadir una entidad `valve` nativa solo para dispositivos con clasificación y DPS de apertura/cierre explícitos; no se adivinan códigos de control.
- Añadir sensores de potencia reactiva/aparente, frecuencia y factor de potencia cuando el esquema Tuya y el dispositivo informan esos valores, con escalas declaradas y canales 1–4.
- Mantener el control cotidiano por LAN y la configuración persistente existente.
- Validar la plataforma Valve contra Home Assistant Core 2026.10.0 y Python 3.14.2.
