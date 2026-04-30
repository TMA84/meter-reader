#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Meter Reader Addon..."

# Read configuration
export CAMERA_URL=$(bashio::config 'camera_url')
export READ_INTERVAL=$(bashio::config 'read_interval_minutes')
export MQTT_ENABLED=$(bashio::config 'mqtt_enabled')
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USERNAME=$(bashio::config 'mqtt_username')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')
export MQTT_TOPIC=$(bashio::config 'mqtt_topic')
export INGRESS_ENTRY=$(bashio::addon.ingress_entry)
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
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
