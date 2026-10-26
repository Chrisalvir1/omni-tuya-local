# Omni Tuya Local v1.12.0 — extracción de entidades y recuperación TCP local

Esta versión mejora la sincronización individual y la recuperación de dispositivos Tuya mediante la red local.

- Recupera candidatos de la subred local cuando el inventario no tiene una IP utilizable y verifica la clave local antes de conservar el host.
- Rechaza las IP públicas recibidas desde Cloud como destino TCP. El control y la lectura de estados siguen siendo locales.
- Tras una prueba TCP válida, actualiza disponibilidad y DPS observados para crear o refrescar las entidades correspondientes.
- Amplía la lectura de funciones y especificaciones declaradas por Tuya, incluidos datapoints de solo lectura y productos con IDs no estándar.
- Conserva escalas, unidades y enumeraciones definidas por el producto sin convertir diagnósticos desconocidos en controles.

La disponibilidad de cada sensor depende de que el firmware lo exponga y de que el dispositivo responda con una clave local válida. Esta publicación no implica una prueba física de todos los modelos ni la instalación en Home Assistant.
