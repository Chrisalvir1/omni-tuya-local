## [1.11.3] - 2026-10-11

- Agregar entidades de cámara para IPC Tuya y comederos de video reconocidos por su categoría/producto.
- Solicitar una URL RTSP temporal a la API oficial de video Tuya y entregarla a la plataforma Camera/Stream de Home Assistant; no guardar ni registrar URLs firmadas.
- Mantener el control y lectura de DPS por LAN, mientras el video usa el relay Cloud de Tuya. El proyecto Tuya debe tener acceso a IoT Video Live Stream; Tuya puede cobrar el tráfico reenviado.
- Pedir una asignación RTSP temporal para capturas y al crear el trabajador de stream de Home Assistant; no registrar ni guardar la URL firmada.
- Documentar que Home Assistant reutiliza su trabajador de cámara: la URL Tuya aún no se renueva automáticamente al vencer; recargar la entrada de Omni crea un trabajador con una asignación nueva.
- Documentar el uso como fuente Home Assistant Camera.UI para un accesorio HAP de Matter All-in-One Chrisalvir. La renovación transparente entre los trabajadores HA y HAP queda pendiente.
- Verificación: cobertura unitaria de asignación RTSP, credenciales ausentes, respuesta inválida y detección del comedero/cámara.

## [1.11.2] - 2026-10-11

- Dejar de convertir códigos de estado de Tuya Cloud en números DPS LAN sin un `dp_id` confirmado por el producto.
- Crear sensores a partir de DPS observados localmente y dejar como desconocido el estado que no tiene lectura LAN; retirar estados de puerta/batería inventados y valores transferidos desde entidades ajenas de Home Assistant.
- Evitar etiquetas especulativas para DPS de contactos, canales switch por defecto y cantidad de canales supuestos en dispositivos desconocidos.
- Corregir `diagnostics`: agrega dispositivos de todas las entradas y no devuelve claves locales.
- Agregar soporte explícito de selección y detección LAN para protocolo 3.2 de TinyTuya.
- Mantener el descubrimiento de DPS desde respuestas LAN y usar esquema de producto Tuya para nombres/funciones solo cuando ofrece el ID DP numérico.
- Validación local: 81 pruebas unitarias, compilación Python y `git diff --check` correctos.

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
