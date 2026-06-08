# Omni Tuya Local v0.4.2 — Ajustes de Conectividad LAN

Esta actualización menor optimiza la capa de red local para mejorar la estabilidad de los dispositivos Tuya de bajo consumo (especialmente apagadores y bombillas inteligentes Wi-Fi como el modelo CB02-SBL).

## 🚀 Mejoras de Red y Estabilidad local

* **Sockets No Persistentes por Defecto**: Deshabilitamos la persistencia de socket (`set_socketPersistent(False)`) para dispositivos y gateways. Varios microcontroladores sencillos de Tuya se bloquean o rechazan comandos cuando un socket TCP se mantiene abierto de forma constante, lo que provocaba que las entidades se mostraran en gris ("No disponible").
* **Mayor Tolerancia de Timeout**: Aumentamos el tiempo de espera del socket de `2.5s` a `5.0s` (`set_socketTimeout(5.0)`). Esto da tiempo suficiente de respuesta a dispositivos con señal Wi-Fi débil o que se encuentren con carga alta de procesamiento.
* **Reintentos de Conexión**: Incrementamos el límite de reintentos de conexión de `1` a `3` antes de marcar un dispositivo como fuera de línea.

---

## 📦 Instalación y Actualización

1. Abre HACS en tu Home Assistant.
2. Actualiza la integración **Omni Tuya Local** a la versión **`v0.4.2`**.
3. **Reinicia Home Assistant** para cargar los nuevos parámetros de comunicación local.
