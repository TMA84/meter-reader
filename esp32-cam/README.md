# ESP32-CAM Firmware (ESPHome)

Minimale Firmware für die ESP32-CAM – nur Kamera + Webserver + LED-Steuerung.
Die gesamte Bildverarbeitung läuft im Meter Reader Addon auf dem HA-Host.

## Unterstützte Boards

Die Konfiguration ist für das **AI-Thinker ESP32-CAM** Board ausgelegt.
Für andere Boards müssen die Pin-Zuweisungen angepasst werden (siehe unten).

## Installation

### Voraussetzungen

- ESPHome installiert (als HA Addon oder lokal via `pip install esphome`)
- USB-zu-Serial Adapter (für den ersten Flash) oder ESP32-CAM mit USB

### Schritte

1. `secrets.yaml` anpassen (WLAN-Daten, Passwörter)
2. Flashen:

```bash
# Erster Flash per USB
esphome run esphome-config.yaml

# Danach OTA (kabellos)
esphome run esphome-config.yaml --device 192.168.1.50
```

## Endpunkte nach dem Flash

| URL | Beschreibung |
|-----|-------------|
| `http://192.168.1.50/` | ESPHome Webserver (Status, Logs) |
| `http://192.168.1.50:8080/` | Kamera-Snapshot (JPEG) |
| `http://192.168.1.50/light/beleuchtung/turn_on?brightness=200` | LED an (0-255) |
| `http://192.168.1.50/light/beleuchtung/turn_off` | LED aus |

## LED-Steuerung vom Addon

Das Meter Reader Addon steuert die LED über den ESPHome Webserver:

```
# LED auf 80% setzen
GET http://192.168.1.50/light/beleuchtung/turn_on?brightness=204

# LED ausschalten
GET http://192.168.1.50/light/beleuchtung/turn_off
```

## Pin-Belegung anderer Boards

### ESP32-S3 (Freenove)

```yaml
i2c:
  - id: camera_i2c
    sda: GPIO4
    scl: GPIO5

esp32_camera:
  i2c_id: camera_i2c
  external_clock:
    pin: GPIO15
    frequency: 20MHz
  data_pins: [GPIO11, GPIO9, GPIO8, GPIO10, GPIO12, GPIO18, GPIO17, GPIO16]
  vsync_pin: GPIO6
  href_pin: GPIO7
  pixel_clock_pin: GPIO13
```

### XIAO ESP32S3 Sense

```yaml
i2c:
  - id: camera_i2c
    sda: GPIO40
    scl: GPIO39

esp32_camera:
  i2c_id: camera_i2c
  external_clock:
    pin: GPIO10
    frequency: 20MHz
  data_pins: [GPIO15, GPIO17, GPIO18, GPIO16, GPIO14, GPIO12, GPIO11, GPIO48]
  vsync_pin: GPIO38
  href_pin: GPIO47
  pixel_clock_pin: GPIO13
```

## Tipps für Stabilität

- **Statische IP** vergeben (ist bereits konfiguriert)
- **Externe Antenne** nutzen (Jumper auf dem Board umlöten auf IPEX-Anschluss)
- **Gutes Netzteil** (min. 2A @ 5V, kurzes Kabel)
- **Framerate niedrig** halten (5fps max, idle 0.1fps) – spart Strom und Wärme
- **PSRAM** muss vorhanden sein (die meisten ESP32-CAM Boards haben es)
