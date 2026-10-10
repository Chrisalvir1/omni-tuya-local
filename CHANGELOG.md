## [1.10.0] - 2026-10-10

- Añadir una entidad `valve` nativa solo para dispositivos con clasificación y DPS de apertura/cierre explícitos; no se adivinan códigos de control.
- Añadir sensores de potencia reactiva/aparente, frecuencia y factor de potencia cuando el esquema Tuya y el dispositivo informan esos valores, con escalas declaradas y canales 1–4.
- Mantener el control cotidiano por LAN y la configuración persistente existente.
- Validar la plataforma Valve contra Home Assistant Core 2026.10.0 y Python 3.14.2.
