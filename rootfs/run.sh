#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Meter Reader Addon..."

# ─── Read addon configuration ──────────────────────────────────────────────────
CAMERA_URL=""
READ_INTERVAL="5"
MQTT_ENABLED="false"
MQTT_HOST="core-mosquitto"
MQTT_PORT="1883"
MQTT_USERNAME=""
MQTT_PASSWORD=""
MQTT_TOPIC="meter-reader/water/value"

if bashio::config.has_value 'camera_url'; then
    CAMERA_URL=$(bashio::config 'camera_url')
fi
if bashio::config.has_value 'read_interval_minutes'; then
    READ_INTERVAL=$(bashio::config 'read_interval_minutes')
fi
if bashio::config.has_value 'mqtt_enabled'; then
    MQTT_ENABLED=$(bashio::config 'mqtt_enabled')
fi
if bashio::config.has_value 'mqtt_host'; then
    MQTT_HOST=$(bashio::config 'mqtt_host')
fi
if bashio::config.has_value 'mqtt_port'; then
    MQTT_PORT=$(bashio::config 'mqtt_port')
fi
if bashio::config.has_value 'mqtt_username'; then
    MQTT_USERNAME=$(bashio::config 'mqtt_username')
fi
if bashio::config.has_value 'mqtt_password'; then
    MQTT_PASSWORD=$(bashio::config 'mqtt_password')
fi
if bashio::config.has_value 'mqtt_topic'; then
    MQTT_TOPIC=$(bashio::config 'mqtt_topic')
fi

export CAMERA_URL
export READ_INTERVAL
export MQTT_ENABLED
export MQTT_HOST
export MQTT_PORT
export MQTT_USERNAME
export MQTT_PASSWORD
export MQTT_TOPIC
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export CONFIG_DIR="/config"
export DATA_DIR="/data"

# ─── Verzeichnisse anlegen ─────────────────────────────────────────────────────
mkdir -p /data/snapshots
mkdir -p /data/logs
mkdir -p /config
mkdir -p /opt/meter-reader/models

# ─── Standard-Konfiguration kopieren wenn nicht vorhanden ─────────────────────
if [ ! -f /config/meter_config.json ]; then
    cp /opt/meter-reader/default_config.json /config/meter_config.json
    bashio::log.info "Standard-Zählerkonfiguration angelegt"
fi

# ─── TFLite-Modell herunterladen wenn nicht vorhanden ─────────────────────────
MODEL_PATH="/opt/meter-reader/models/dig-class11.tflite"
MODEL_URL="https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/neuralnets/dig-class11/dig-class11-v2.3.tflite"
MODEL_URL_FALLBACK="https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/neuralnets/dig-class11/dig-class11-v2.2.tflite"

if [ ! -f "${MODEL_PATH}" ]; then
    bashio::log.info "TFLite-Modell nicht gefunden – lade herunter..."
    if wget -q --timeout=30 -O "${MODEL_PATH}" "${MODEL_URL}"; then
        bashio::log.info "Modell erfolgreich heruntergeladen: dig-class11-v2.3.tflite"
    elif wget -q --timeout=30 -O "${MODEL_PATH}" "${MODEL_URL_FALLBACK}"; then
        bashio::log.info "Modell heruntergeladen (Fallback): dig-class11-v2.2.tflite"
    else
        bashio::log.warning "Modell konnte nicht heruntergeladen werden – manuelle Installation nötig"
        bashio::log.warning "Pfad: ${MODEL_PATH}"
        bashio::log.warning "URL: ${MODEL_URL}"
        rm -f "${MODEL_PATH}"
    fi
else
    bashio::log.info "TFLite-Modell vorhanden: ${MODEL_PATH}"
fi

# ─── Start ─────────────────────────────────────────────────────────────────────
bashio::log.info "Kamera-URL: ${CAMERA_URL}"
bashio::log.info "Ablesungsintervall: ${READ_INTERVAL} Minuten"
bashio::log.info "MQTT: ${MQTT_ENABLED}"

exec python3 /opt/meter-reader/app.py
