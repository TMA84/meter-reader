#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set +u

bashio::log.info "Starting Meter Reader Addon..."

# Wait for Supervisor API to be ready
bashio::log.info "Waiting for Supervisor API..."
for i in $(seq 1 30); do
    if bashio::supervisor.ping 2>/dev/null; then
        break
    fi
    sleep 1
done

# Read configuration from options
export CAMERA_URL="$(bashio::config 'camera_url' 2>/dev/null || echo 'http://192.168.1.50:8080/snapshot')"
export READ_INTERVAL="$(bashio::config 'read_interval_minutes' 2>/dev/null || echo '5')"
export MQTT_ENABLED="$(bashio::config 'mqtt_enabled' 2>/dev/null || echo 'false')"
export MQTT_HOST="$(bashio::config 'mqtt_host' 2>/dev/null || echo 'core-mosquitto')"
export MQTT_PORT="$(bashio::config 'mqtt_port' 2>/dev/null || echo '1883')"
export MQTT_USERNAME="$(bashio::config 'mqtt_username' 2>/dev/null || echo '')"
export MQTT_PASSWORD="$(bashio::config 'mqtt_password' 2>/dev/null || echo '')"
export MQTT_TOPIC="$(bashio::config 'mqtt_topic' 2>/dev/null || echo 'meter-reader/water/value')"
export INGRESS_ENTRY="$(bashio::addon.ingress_entry 2>/dev/null || echo '/')"
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
