#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Meter Reader Addon..."

# Read configuration
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

# Ensure data directories exist
mkdir -p /data/snapshots
mkdir -p /data/logs
mkdir -p /config

# Initialize config file if not exists
if [ ! -f /config/meter_config.json ]; then
    cp /opt/meter-reader/default_config.json /config/meter_config.json
    bashio::log.info "Created default meter configuration"
fi

bashio::log.info "Camera URL: ${CAMERA_URL}"
bashio::log.info "Read interval: ${READ_INTERVAL} minutes"
bashio::log.info "MQTT enabled: ${MQTT_ENABLED}"

# Start the application
exec python3 /opt/meter-reader/app.py
