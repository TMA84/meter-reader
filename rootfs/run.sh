#!/usr/bin/with-contenv bash
# shellcheck shell=bash

echo "[INFO] Starting Meter Reader Addon..."

# Read config directly from options.json (no Supervisor API needed)
CONFIG_PATH="/data/options.json"

if [ -f "$CONFIG_PATH" ]; then
    export CAMERA_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('camera_url','http://192.168.1.50:8080/snapshot'))")
    export READ_INTERVAL=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('read_interval_minutes',5))")
    export MQTT_ENABLED=$(python3 -c "import json; print(str(json.load(open('$CONFIG_PATH')).get('mqtt_enabled',False)).lower())")
    export MQTT_HOST=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('mqtt_host','core-mosquitto'))")
    export MQTT_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('mqtt_port',1883))")
    export MQTT_USERNAME=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('mqtt_username',''))")
    export MQTT_PASSWORD=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('mqtt_password',''))")
    export MQTT_TOPIC=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('mqtt_topic','meter-reader/water/value'))")
else
    echo "[WARN] No options.json found, using defaults"
    export CAMERA_URL="http://192.168.1.50:8080/snapshot"
    export READ_INTERVAL="5"
    export MQTT_ENABLED="false"
    export MQTT_HOST="core-mosquitto"
    export MQTT_PORT="1883"
    export MQTT_USERNAME=""
    export MQTT_PASSWORD=""
    export MQTT_TOPIC="meter-reader/water/value"
fi

export INGRESS_ENTRY="${INGRESS_ENTRY:-/}"
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export CONFIG_DIR="/config"
export DATA_DIR="/data"

# Ensure data directories exist
mkdir -p /data/snapshots
mkdir -p /data/logs
mkdir -p /config

# Initialize config file if not exists
if [ ! -f /config/meter_config.json ]; then
    cp /opt/meter-reader/default_config.json /config/meter_config.json
    echo "[INFO] Created default meter configuration"
fi

echo "[INFO] Camera URL: ${CAMERA_URL}"
echo "[INFO] Read interval: ${READ_INTERVAL} minutes"
echo "[INFO] MQTT enabled: ${MQTT_ENABLED}"

# Start the application
exec python3 /opt/meter-reader/app.py
