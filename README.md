# Meter Reader – Home Assistant Addon

Ein Home Assistant Addon zur automatischen Ablesung von Wasser-, Gas- und Stromzählern per Kamera. Die Bildaufnahme erfolgt über eine ESP32-CAM mit ESPHome, die Ziffernerkennung läuft ressourcenschonend auf dem HA-Host mittels TFLite.

## Warum?

Projekte wie [AI on the Edge](https://github.com/jomjol/AI-on-the-edge-device) laufen komplett auf dem ESP32 – das führt häufig zu Abstürzen, Speicherproblemen und instabilem Betrieb. Meter Reader trennt Kamera und Verarbeitung: Der ESP32 macht nur noch Fotos (stabil, minimaler RAM-Verbrauch), die rechenintensive Erkennung läuft auf dem HA-Host.

## Features

- **Stabile Architektur** – ESP32-CAM nur als Kamera, Verarbeitung auf dem HA-Host
- **TFLite-Ziffernerkennung** – Nutzt die bewährten Modelle aus AI on the Edge (dig-class11)
- **Moderne Web-Oberfläche** – Dark-Theme UI mit Dashboard, ROI-Editor, Verlauf und Einstellungen
- **LED-Steuerung** – Automatisch: LED an → Verzögerung → Foto → LED aus
- **Kamera-Kontrolle** – Helligkeit, Kontrast, Sättigung, Rotation (1°-genau) direkt aus der App
- **Plausibilitätsprüfung** – Kein Rückwärtslaufen, Max-Rate-Begrenzung, Ausreißer-Filter
- **MQTT-Support** – Vollständig konfigurierbare Broker-Verbindung
- **Home Assistant Integration** – Automatischer Sensor (`sensor.meter_reader_water`) für das Energie-Dashboard
- **Ingress** – Web-UI direkt in der HA-Sidebar

## Architektur

```
ESP32-CAM (ESPHome)              Home Assistant (Addon)
┌──────────────────┐             ┌─────────────────────────┐
│ • Kamera-Snapshot│◄── HTTP ───▶│ • Bild holen            │
│ • LED-Steuerung  │             │ • Ziffern erkennen      │
│ • Webserver      │             │ • Plausibilität prüfen  │
│                  │             │ • HA Sensor updaten     │
│ Stabil, <20KB RAM│             │ • MQTT publishen        │
└──────────────────┘             │ • Web-UI bereitstellen  │
                                 └─────────────────────────┘
```

## Screenshots

| Dashboard | ROI-Editor | Kamera-Einstellungen |
|-----------|-----------|---------------------|
| Aktueller Wert, Status, Live-Bild | Ziffernbereiche visuell markieren | LED, Helligkeit, Rotation |

## Installation

### 1. ESP32-CAM flashen

ESPHome-Konfiguration liegt in [`esp32-cam/`](esp32-cam/). Unterstützt AI-Thinker ESP32-CAM und kompatible Boards.

```bash
esphome run esp32-cam/esphome-config.yaml
```

### 2. Addon installieren

Repository in Home Assistant hinzufügen:

[![Open your Home Assistant instance and show the add add-on repository dialog.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDEIN-USERNAME%2Fmeter-reader-addon)

### 3. TFLite-Modell herunterladen

Das Modell `dig-class11.tflite` von [AI on the Edge](https://github.com/jomjol/AI-on-the-edge-device/tree/main/sd-card/config/models) herunterladen und in den Addon-Config-Ordner legen.

### 4. Konfigurieren

- Kamera-URL eintragen (z.B. `http://192.168.1.50:8080/`)
- ROIs über den visuellen Editor setzen
- Fertig – der Zähler wird automatisch abgelesen

## Konfiguration

Alle Einstellungen sind sowohl über die HA Addon-Konfiguration als auch über die Web-Oberfläche änderbar.

| Einstellung | Beschreibung |
|-------------|-------------|
| Kamera-URL | Snapshot-Endpunkt der ESP32-CAM |
| Intervall | Ablesefrequenz (1–60 Minuten) |
| MQTT | Broker, Port, Auth, Topic |
| LED | Intensität + Verzögerung vor Aufnahme |
| Bild | Helligkeit, Kontrast, Sättigung, Rotation |
| ROIs | Position und Größe der Ziffernbereiche |
| Plausibilität | Max-Rate, Nachkommastellen |

## Unterstützte Hardware

**ESP32-CAM Boards:**
- AI-Thinker ESP32-CAM (Standard)
- ESP32-S3 mit OV2640
- Freenove ESP32-S3-CAM
- XIAO ESP32S3 Sense

**Home Assistant Host:**
- Home Assistant Yellow (CM4)
- Raspberry Pi 4/5
- x86/NUC
- Jedes System mit Docker/HA OS

## Technologie

- **Backend:** Python, Flask, OpenCV, TFLite Runtime
- **Frontend:** Vanilla JS, CSS (kein Framework – schnell und leichtgewichtig)
- **ESP32:** ESPHome
- **Modelle:** TFLite (dig-class11 aus AI on the Edge)

## Lizenz

MIT

## Credits

- Ziffernerkennungs-Modelle: [jomjol/AI-on-the-edge-device](https://github.com/jomjol/AI-on-the-edge-device)
- Inspiration: Die großartige AI on the Edge Community
