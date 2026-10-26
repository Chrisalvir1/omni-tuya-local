# Auditoría de Omni Tuya Local — 25 de octubre de 2026

Base auditada: `76dd2b0b65d1b0b0d3505746156c034f83a1cc9c` (1.11.11). Correcciones propuestas: 1.12.0. Alcance: código de las 17 plataformas, alta individual, importación Cloud, inventario, transporte TCP, recuperación de red, diagnóstico, pruebas, CI y contrato de exportación a Matter All-in-One Chrisalvir.

## Evidencia de la instalación

Inspección mediante la terminal autenticada de Home Assistant, sin publicar credenciales: HA Core 2026.10.3, Omni 1.11.11, **69 dispositivos en el inventario y ninguno con `tuya_functions`**. Esto confirma que la ausencia del esquema afecta también a los dispositivos ya enlazados.

Consulta real de Smart Plug Duo: `getfunctions()` devuelve `result.functions` con códigos sin IDs; `getdps()` devuelve `result.functions` y `result.status` con `dp_id`. El producto declara dos interruptores (DP 1/2) y dos temporizadores (DP 9/10); esa respuesta no declara medidores de energía. No corresponde inventar corriente, potencia o voltaje para ese dispositivo.

El usuario exporta con `Chrisalvir1/matter-all-in-one-chrisalvir`, no exclusivamente con HomeKit Bridge. Se inspeccionaron los filtros de `platform.ts` y los servicios secundarios de `hap-generic-accessory.ts`: usan las clases/unidades de HA y los miembros del registro de dispositivos. Por eso corregir solamente nombres de entidades no basta.

## Hallazgos corregidos

| Prioridad | Hallazgo y efecto | Corrección |
|---|---|---|
| P1 | Alta individual guarda una ficha preliminar; el arranque prefiere inventario y pierde IP/protocolo/DPS finales. | Persistir la ficha final antes de crear la entrada. |
| P1 | `result.functions` anidado se descarta. | Normalizar ambas formas de respuesta. |
| P1 | Solo se consultan funciones; faltan IDs numéricos y telemetría de solo lectura. | Consultar especificaciones `getdps`; unir funciones/estados por código y conservar permisos. |
| P1 | Esquema LAN descarta DP 7–16, 21–26, 38–40 y booleanos altos. | Guardar todo DP escalar observado; separar descubrimiento de permisos de escritura. |
| P1 | Cantidad de canales se confunde con ID del DP. | Preferir IDs del esquema y mapas explícitos; soportar DP 20/101/105. |
| P1 | Todo dominio `switch` pierde sus sensores, incluidos enchufes. | Retirar la exclusión y conservar telemetría real. |
| P1 | Limpieza borra sensores, helpers y entidades ajenas por heurísticas. | Limitar limpieza a entidades primarias del dominio anterior, propias de la entrada. |
| P1 | Sincronizar solo cambia el coordinador; entidades viejas mantienen metadatos. | Recargar las entradas enlazadas para reconstruir clases, unidades y capacidades. |
| P1 | Una corrección DP 1 → 20 podría generar otro identificador para Casa. | Migración inequívoca de un único canal conservando `entity_id`; no sobrescribir colisiones. |
| P1 | Sensores del esquema no aparecen antes del primer sondeo. | Crear los sensores declarados con estado desconocido hasta lectura LAN; no usar caché Cloud como lectura. |
| P1 | Alta ignora la prueba de conexión fallida. | Mostrar error; conservar opción explícita de configuración diferida dejando IP vacía. |
| P1 | Estados vacíos o errores con campo DPS se consideran conexión válida. | Exigir un diccionario DPS no vacío sin errores. |
| P1 | Subdispositivo con solo IP del gateway se considera sin host. | Validar `effective_host` e invalidar cliente ante cambios del gateway/nodo/clave. |
| P2 | Luces DP 20–24 no se identifican; booleano DP 2 se interpreta como brillo. | Resolver capacidades por esquema y familia de protocolo; excluir booleanos del brillo. |
| P2 | Presencia cableada se trata como sensor durmiente. | Retirar clasificación global por dominio binario. |
| P2 | Sondeo de sensores durmientes se cancela antes del timeout del socket. | Dar presupuesto al transporte existente. |
| P2 | `updatedps` usa únicamente IDs de enchufes tradicionales. | Consultar los IDs conocidos del producto y el inventario LAN. |
| P2 | Escala del producto se aplica solo a unas pocas magnitudes. | Aplicar exponente declarado a sensores numéricos y conservar unidades del esquema. |
| P2 | Enumeraciones como nivel de batería reciben clase numérica inválida. | Conservarlas como texto; agregar códigos estándar de temperatura/humedad/batería. |
| P2 | Una ubicación con “puerta” transforma luces/cerraduras en contactos. | Respetar categorías conocidas y actuadores explícitos. |
| P2 | `homekit_type` personalizado no configura HomeKit Bridge. | Publicar clase nativa `outlet`; mantener atributos compatibles con otros consumidores. |
| P2 | Sincronización Cloud puede regresar protocolo LAN verificado a 3.3. | Preservar protocolo de dispositivos existentes; solo usuario/LAN lo corrigen. |
| P2 | Redescubrimiento puede asociar una identidad real por una IP reutilizada. | Priorizar identificadores/alias/MAC; coincidencia solo por IP para resultados sin identidad. |
| P2 | UDP sin versión anuncia por defecto 3.3. | No modificar protocolo si el anuncio no incluye versión. |
| P2 | Listener no reconecta ante errores TinyTuya devueltos como diccionario. | Reconectar también ante errores sin excepción. |
| P2 | Diagnóstico no redacta variantes `key`, `localKey`, tokens. | Ampliar redacción. |
| P2 | Error Cloud sin credenciales referencia `HomeAssistantError` no importado. | Corregir importación; análisis estático en CI. |

## Dependencias y compatibilidad

Verificación de registros oficiales realizada durante esta auditoría:

- TinyTuya **1.20.0** sigue siendo la última versión publicada: se mantiene el pin.
- Requests 2.34.2, cryptography 50.0.2 y colorama 0.4.6 son las versiones resueltas en el entorno aislado de auditoría. Las dependencias compartidas de HA no deben actualizarse manualmente sobre sus restricciones.
- Home Assistant más reciente de la rama: **2026.10.4**; la instalación observada usa 2026.10.3. No se actualiza Core implícitamente con una integración.
- CI actualiza checkout a v7.0.1 y setup-python a v7.1.0; agrega Ruff y matriz con Core 2026.10.0/2026.10.4. Las pruebas de válvula quedan en la suite común y se elimina el workflow duplicado.
- `pip-audit` sobre la resolución de TinyTuya y sus dependencias: **sin vulnerabilidades conocidas** en esa resolución. Esto no certifica los paquetes instalados del usuario, HA completo ni el firmware.

Fuentes: [TinyTuya en PyPI](https://pypi.org/pypi/tinytuya/json), [API de TinyTuya](https://github.com/jasonacox/tinytuya/blob/master/tinytuya/Cloud.py), [HA en PyPI](https://pypi.org/pypi/homeassistant/json), [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-python](https://github.com/actions/setup-python/releases/tag/v7.1.0).

## Límites concretos que la auditoría no considera resueltos

1. **Video Cloud**: `camera.py` solicita RTSP temporal a Tuya. No cumple un objetivo de video completamente local. El control DPS sigue por TCP. Un firmware sin RTSP/ONVIF local no obtiene video LAN por actualizar una librería.
2. **Perfiles de actuadores**: clima, ventiladores, cerraduras, cortinas, alarmas, aspiradoras, números y selectores conservan plantillas con IDs/opciones convencionales. El esquema ya se conserva, pero su traducción completa a cada plataforma requiere perfiles verificados por producto. No se afirma compatibilidad universal de escritura.
3. **Estados especulativos heredados**: alarmas y aspiradoras conservan algunos estados por defecto; sensores eléctricos sin escala conservan conversiones históricas por magnitud. Requieren revisión por producto antes de certificar precisión física.
4. **Sesiones de gateway y push**: cada cliente mantiene su sesión; no hay multiplexor compartido por gateway. Dos sockets en determinados firmwares pueden competir. Las pruebas de locks no demuestran compatibilidad de todos los gateways.
5. **Descubrimiento**: se conserva UDP local para anuncios y TCP 6668 para lecturas/comandos. “Local” no significa eliminar UDP de descubrimiento. La recuperación de dirección sin anuncios tiene límites; escaneo de subred sigue suponiendo /24.
6. **Identificación sin esquema**: observar un número no revela su significado. Se conserva un sensor DPS neutral; no se habilita escritura arbitraria sobre booleanos desconocidos. Si Tuya no ofrece `dp_id`, no se inventa uno por posición.
7. **Sensores dormidos/BLE/Zigbee**: pueden no aceptar TCP directo o no responder mientras duermen. Necesitan gateway compatible y/o evento de despertar; sincronizar no cambia el firmware.
8. **Exportación real**: Matter All-in-One usa filtros propios y perfiles HAP/Matter. Una entidad existente en HA puede requerir incluirse y reconstruir servicios en el puente. Algunas magnitudes no tienen representación nativa en Apple Casa. La caché de nombres/servicios no se valida con pruebas unitarias.
9. **Migración multicanal**: se preservan IDs existentes y se migra automáticamente solo un único canal inequívoco. Cambios ambiguos de productos multicanal requieren comparar su esquema con entidades existentes, sin borrar automatizaciones por inferencia.

## Validación automatizada

- Base: 92 pruebas unitarias existentes aprobadas, aunque no detectaban los defectos anteriores.
- Corrección: 115 pruebas unitarias aprobadas en el entorno Python 3.12; nuevas regresiones cubren importación anidada, alta individual, sensores desconocidos, IDs altos, escalas y migración.
- 16 pruebas con HA Core real y Python 3.14.2: incluyen contratos de entidades, comandos rechazados, WebSocket, flujo individual y enrutador de HomeKit. Se registra por separado la versión exacta de Core utilizada en cada ejecución.
- Ruff (`--select F`), compilación Python y comprobación del diff.
- Las dependencias de HomeKit/cámara se instalan para importar sus módulos reales, evitando considerar mocks de plataformas como validación de Core.

## Procedimiento para dispositivos ya enlazados

1. Respaldar la carpeta de la integración y el inventario; conservar los registros de dispositivos/entidades y el almacenamiento del puente.
2. Instalar la corrección y validar configuración antes de reiniciar HA.
3. Ejecutar una sincronización explícita de Omni para obtener esquemas. El proceso recarga las entradas existentes sin borrar el inventario.
4. Comparar por dispositivo: ID Cloud/LAN, DP del producto, entidad HA, clase/unidad, lectura TCP y exportación en Matter All-in-One. No publicar claves locales en el informe.
5. Reconstruir/actualizar servicios del puente mediante sus controles existentes, conservando emparejamientos. Verificar en Casa órdenes y cambios de estado; no accionar cerraduras, alarmas, comederos o equipos de calor solo como prueba de conectividad.
6. Probar reinicio y recuperación de red. Registrar dispositivos no accesibles por LAN y diferencias de esquema. La ausencia de lectura debe seguir visible como desconocido/no disponible.

El cierre de la auditoría de código no equivale a confirmar funcionamiento físico de los 69 dispositivos ni a que la corrección esté publicada como release estable.
