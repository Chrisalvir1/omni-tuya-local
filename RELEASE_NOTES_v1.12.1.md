# Omni Tuya Local v1.12.1

## Correcciones

- Robotina con modelo `A1-ROPVACNIC` se clasifica como `vacuum` aunque Tuya Cloud no entregue la categoría `sd` ni el modelo en el nivel superior de sus metadatos.
- El asistente de alta ignora versiones de firmware incompatibles con TinyTuya y usa solo protocolos LAN soportados.
- El escaneo y alta manual descartan hosts públicos; la conexión del dispositivo permanece TCP local.
- El escaneo TinyTuya tolera respuestas con estructura inesperada.
- Evita publicar DP de tiempo/fallo como corriente o potencia sin metadatos de función; los controles de la aspiradora permanecen en la entidad `vacuum` con sus comandos Tuya.

## Límites

Omni solo crea entidades respaldadas por DPS/funciones reales que el dispositivo entregue por LAN o que su ficha Tuya describa. Esta versión no se ha validado todavía contra la Robotina física.
