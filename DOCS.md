# Meter Reader - Home Assistant Addon

Liest analoge und digitale Zähler (Wasser, Gas, Strom) per Kamera aus.
Die Bildaufnahme erfolgt über eine externe ESP32-CAM (mit ESPHome),
die Verarbeitung läuft ressourcenschonend im Addon auf deinem HA-Host.

## Voraussetzungen

- ESP32-CAM mit ESPHome (liefert Snapshot per HTTP)
- TFLite-Modell `dig-class11.tflite` (aus dem AI-on-the-edge-device Projekt)

## Installation

1. Dieses Repository als lokales Addon hinzufügen
2. Das Modell `dig-class11.tflite` herunterladen und in den Addon-Config-Ordner legen
3. Addon starten und über die Web-Oberfläche konfigurieren

## Modell herunterladen

Das Modell findest du hier:
https://github.com/jomjol/AI-on-the-edge-device/tree/main/sd-card/config/models

Lade `dig-class11.tflite` herunter und kopiere es nach:
`/addon_configs/local_meter-reader/models/`

## Konfiguration

### Addon-Einstellungen

| Option | Beschreibung |
|--------|-------------|
| `camera_url` | URL zum Snapshot der ESP32-CAM (z.B. `http://192.168.1.50:8080/snapshot`) |
| `read_interval_minutes` | Ableseintervall in Minuten (Standard: 5) |
| `mqtt_enabled` | MQTT-Veröffentlichung aktivieren |
| `mqtt_topic` | MQTT-Topic für den Zählerstand |

### ROI-Konfiguration (Web-Oberfläche)

1. Öffne die Web-Oberfläche über das Seitenmenü in HA
2. Gehe zu "Konfiguration"
3. Klicke "Bild laden" um das aktuelle Kamerabild zu sehen
4. Füge für jede Ziffer einen ROI-Bereich hinzu
5. Passe X, Y, Breite und Höhe an, bis jede Ziffer einzeln eingerahmt ist
6. Klicke "ROIs testen" um die Erkennung zu prüfen
7. Speichere die Konfiguration

## ESP32-CAM Setup (ESPHome)

Minimale ESPHome-Konfiguration für die Kamera:

```yaml
esphome:
  name: wasserzaehler-cam

esp32:
  board: esp32cam

wifi:
  ssid: "DeinWLAN"
  password: "DeinPasswort"
  manual_ip:
    static_ip: 192.168.1.50
    gateway: 192.168.1.1
    subnet: 255.255.255.0

esp32_camera:
  name: "Wasserzaehler"
  external_clock:
    pin: GPIO0
    frequency: 20MHz
  i2c_pins:
    sda: GPIO26
    scl: GPIO27
  data_pins: [GPIO5, GPIO18, GPIO19, GPIO21, GPIO36, GPIO39, GPIO34, GPIO35]
  vsync_pin: GPIO25
  href_pin: GPIO23
  pixel_clock_pin: GPIO22
  power_down_pin: GPIO32
  resolution: 800x600
  jpeg_quality: 10

esp32_camera_web_server:
  - port: 8080
    mode: snapshot
```

## Sensor in Home Assistant

Das Addon erstellt automatisch einen Sensor:
- `sensor.meter_reader_water` - Aktueller Zählerstand in m³

Dieser kann direkt im Energie-Dashboard verwendet werden.
