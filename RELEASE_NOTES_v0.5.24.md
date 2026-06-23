# Omni Tuya Local 0.5.24

- Corrige el perfil de comederos Tuya con cámara: la alimentación manual usa el DP numérico declarado por el producto (`feed_publish`/`manual_feed`).
- Guarda permanentemente las porciones seleccionadas para que `Alimentar ahora` use el valor correcto después de reinicios, cambios de IP y redescubrimiento.
- La sincronización cloud importa el esquema oficial de funciones/DPS del producto y conserva las preferencias locales.
- `Limpiar tolva` ya no usa DPS adivinados; sólo se expone cuando el producto declara un comando de limpieza/vaciado.
