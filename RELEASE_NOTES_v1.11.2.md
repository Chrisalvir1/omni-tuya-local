# Omni Tuya Local v1.11.2

Esta actualización hace más estricta la separación entre el esquema de producto de Tuya Cloud y los DPS numéricos observados del dispositivo por LAN.

## Cambios

- No convertir códigos cloud como `battery_percentage` o `switch_1` en números DPS LAN sin un `dp_id` explícito del producto.
- Construir entidades de telemetría a partir de lecturas LAN y esquema de producto verificable; valores no leídos permanecen desconocidos.
- Retirar estados supuestos para contactos, batería y tamper, además de valores copiados desde entidades genéricas de Home Assistant.
- Evitar canales y semánticas DPS especulativos en dispositivos sin esquema confiable.
- Corregir el servicio `diagnostics` para agregar los dispositivos de todas las entradas y excluir claves locales.
- Añadir selección y detección del protocolo LAN 3.2 de TinyTuya. Se mantienen 3.1, 3.3, 3.4 y 3.5.

## Verificación

- 81 pruebas unitarias aprobadas.
- Compilación de `custom_components/omni_tuya_local` aprobada.
- `git diff --check` limpio.

La lectura física de cada dispositivo sigue dependiendo de que esté accesible en la red local, tenga una dirección correcta y responda al protocolo/clave configurados. El esquema Cloud puede no proporcionar los IDs DPS en todos los productos.
