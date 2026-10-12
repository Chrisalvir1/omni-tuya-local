## [1.11.11] - 2026-10-12

- Incluye la reparación comprobada del WebSocket de cámara y conserva la inferencia de batería y estadísticas de la versión instalada 1.11.8.
- Sincroniza la versión del manifiesto, los diagnósticos y el número de compilación de Omni.

## [1.11.10] - 2026-10-12

- Corrige ambos errores del WebSocket de cámara: firma de tres argumentos de HA y autorización mediante `@websocket_api.require_admin` en lugar del método inexistente de la conexión.
- Prueba contra los decoradores reales de Home Assistant: asignación autorizada correcta y denegación a usuarios sin permiso de administrador. Ejecutada también en el contenedor HA de la instalación afectada.

## [1.11.9] - 2026-10-12

- Corrige el controlador WebSocket `omni_tuya_local/camera_stream`: recibe los tres argumentos de Home Assistant (`hass`, conexión, mensaje). Antes fallaba con TypeError antes de asignar el RTSP y MIAO terminaba usando HLS sin vídeo.
- Añade una prueba de regresión que ejecuta el controlador con el contrato real de despacho. Conserva la autorización de administrador.
- Verificación directa en la instalación: Tuya asigna RTSP y FFprobe detecta H.264 640×360 a 15 fps y audio PCM μ-law a 8 kHz sin 401/404. La validación de HomeKit después de cargar la corrección se informa por separado.

## [1.11.7] - 2026-10-11

- Restaurar `device_class: battery`, unidad `%` y `state_class: measurement` para sensores de batería cuyo dispositivo Tuya expone el DPS numérico sin reenviar `battery_percentage`. Evita el aviso de estadísticas de Home Assistant para SENSOR PUERTA OFICINA.

## [1.11.6] - 2026-10-11

- Corregir la captura de imagen de cámaras Tuya para Home Assistant 2026.10: pasar el ancho y alto como argumentos con nombre a FFmpeg, evitando que se interpreten como formato/comando y fallen con `AttributeError: 'int' object has no attribute 'read'`.
- Agregar una prueba de regresión que verifica la firma actual de FFmpeg y las dimensiones de imagen.

## [1.11.5] - 2026-10-11

- Mantener disponible la entidad de cámara cuando falla el sondeo Tuya por LAN, siempre que Omni tenga credenciales Cloud configuradas; la asignación RTSP usa Tuya Cloud.
- Reconocer comederos con cámara de categoría `cwwsq` solo cuando los metadatos confirman cámara/video, evitando crear cámaras falsas para comederos normales.
- Agregar pruebas de disponibilidad Cloud y detección de Smart Video Feeder.

## [1.11.4] - 2026-10-11

- Agregar un comando WebSocket de Home Assistant autenticado y limitado a las entidades de cámara de Omni para asignar una URL RTSP firmada nueva al comenzar cada sesión HAP.
- Actualizar Matter All-in-One Chrisalvir para solicitar esa URL al iniciar cada sesión Camera.UI/HAP, sin reutilizar deliberadamente la URL Tuya anterior cuando una renovación falla.
- Evitar enviar el token de acceso de Home Assistant al origen RTSP directo de Tuya; no persistir ni registrar la URL firmada.
- Tras reiniciar Home Assistant, la siguiente apertura HAP solicita una asignación nueva. El flujo requiere IoT Video Live Stream activo, conectividad con Tuya y el puente HAP actualizado.
- Añadir pruebas del comando WebSocket y la solicitud de renovación. La disponibilidad del video depende de que Tuya y la red respondan.

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
