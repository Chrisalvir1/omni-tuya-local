# Release v1.1.7 — Estados Confirmados para Sensores de Puerta Wi-Fi

Los sensores de contacto Wi-Fi que están en reposo profundo ya no se muestran
como **Cerrado** cuando Omni Tuya Local no ha recibido un DPS real. En ese
caso Home Assistant muestra el estado **Desconocido** hasta recibir una lectura
confirmada de la LAN o de un anuncio UDP del dispositivo.

El sondeo inmediato que ocurre al despertar el sensor ahora permite hasta ocho
segundos, alineado con el tiempo de espera de TinyTuya. Antes se cancelaba a
los dos segundos, por lo que podía perder respuestas válidas del SHOME-142 y
otros contactos Wi-Fi LAN 3.3.
