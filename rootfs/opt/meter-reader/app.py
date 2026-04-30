"""Meter Reader - Home Assistant Addon
Main application: Flask web UI + scheduled meter reading.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import schedule
from flask import Flask, jsonify, render_template, request, send_from_directory

from meter_engine import MeterEngine

# Static paths
INGRESS_ENTRY = os.environ.get("INGRESS_ENTRY", "/")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")


# ─── Settings Management ──────────────────────────────────────────────────────

# Default settings (from environment / HA addon config)
DEFAULT_SETTINGS = {
    "camera_url": os.environ.get("CAMERA_URL", "http://192.168.1.50:8080/snapshot"),
    "read_interval_minutes": int(os.environ.get("READ_INTERVAL", "5")),
    "mqtt_enabled": os.environ.get("MQTT_ENABLED", "false").lower() == "true",
    "mqtt_host": os.environ.get("MQTT_HOST", "core-mosquitto"),
    "mqtt_port": int(os.environ.get("MQTT_PORT", "1883")),
    "mqtt_username": os.environ.get("MQTT_USERNAME", ""),
    "mqtt_password": os.environ.get("MQTT_PASSWORD", ""),
    "mqtt_topic": os.environ.get("MQTT_TOPIC", "meter-reader/water/value"),
}


def load_settings() -> dict:
    """Load settings from file, falling back to defaults (env/addon config)."""
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(settings: dict):
    """Persist settings to file."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# Active settings (mutable at runtime)
app_settings = load_settings()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{DATA_DIR}/logs/meter-reader.log"),
    ],
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(
    __name__,
    template_folder="/opt/meter-reader/web/templates",
    static_folder="/opt/meter-reader/web/static",
)

# Meter engine
engine = MeterEngine(
    config_path=f"{CONFIG_DIR}/meter_config.json",
    models_path="/opt/meter-reader/models",
    data_path=DATA_DIR,
)


# ─── API Routes ────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Main web UI."""
    return render_template("index.html", ingress_entry=INGRESS_ENTRY)


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current meter configuration."""
    config = engine.get_config()
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def save_config():
    """Save meter configuration."""
    data = request.get_json()
    engine.save_config(data)
    return jsonify({"status": "ok"})


@app.route("/api/snapshot", methods=["GET"])
def get_snapshot():
    """Get current camera snapshot."""
    img_path = engine.capture_snapshot(app_settings["camera_url"])
    if img_path:
        return send_from_directory(
            os.path.dirname(img_path), os.path.basename(img_path)
        )
    return jsonify({"error": "Could not capture snapshot"}), 500


@app.route("/api/snapshot/annotated", methods=["GET"])
def get_annotated_snapshot():
    """Get snapshot with ROI overlay."""
    img_path = engine.capture_annotated_snapshot(app_settings["camera_url"])
    if img_path:
        return send_from_directory(
            os.path.dirname(img_path), os.path.basename(img_path)
        )
    return jsonify({"error": "Could not capture snapshot"}), 500


@app.route("/api/read", methods=["POST"])
def trigger_read():
    """Manually trigger a meter reading."""
    result = perform_reading()
    return jsonify(result)


@app.route("/api/readings", methods=["GET"])
def get_readings():
    """Get recent readings."""
    limit = request.args.get("limit", 100, type=int)
    readings = engine.get_readings(limit=limit)
    return jsonify(readings)


@app.route("/api/roi/test", methods=["POST"])
def test_roi():
    """Test ROI configuration on current image."""
    data = request.get_json()
    result = engine.test_roi(app_settings["camera_url"], data.get("rois", []))
    return jsonify(result)


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get addon status."""
    return jsonify(
        {
            "camera_url": app_settings["camera_url"],
            "read_interval": app_settings["read_interval_minutes"],
            "mqtt_enabled": app_settings["mqtt_enabled"],
            "mqtt_topic": app_settings["mqtt_topic"],
            "last_reading": engine.last_reading,
            "last_read_time": engine.last_read_time,
            "uptime": engine.get_uptime(),
        }
    )


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current application settings."""
    # Don't expose password in plain text - mask it
    safe_settings = app_settings.copy()
    if safe_settings.get("mqtt_password"):
        safe_settings["mqtt_password"] = "••••••••"
    return jsonify(safe_settings)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update application settings at runtime."""
    global app_settings
    data = request.get_json()

    # Validate
    errors = []
    if "camera_url" in data:
        if not isinstance(data["camera_url"], str) or not data["camera_url"].startswith("http"):
            errors.append("camera_url muss eine gültige HTTP-URL sein")
    if "read_interval_minutes" in data:
        val = data["read_interval_minutes"]
        if not isinstance(val, int) or val < 1 or val > 60:
            errors.append("read_interval_minutes muss zwischen 1 und 60 liegen")
    if "mqtt_enabled" in data:
        if not isinstance(data["mqtt_enabled"], bool):
            errors.append("mqtt_enabled muss true oder false sein")
    if "mqtt_host" in data:
        if not isinstance(data["mqtt_host"], str) or len(data["mqtt_host"]) == 0:
            errors.append("mqtt_host darf nicht leer sein")
    if "mqtt_port" in data:
        val = data["mqtt_port"]
        if not isinstance(val, int) or val < 1 or val > 65535:
            errors.append("mqtt_port muss zwischen 1 und 65535 liegen")
    if "mqtt_topic" in data:
        if not isinstance(data["mqtt_topic"], str) or len(data["mqtt_topic"]) == 0:
            errors.append("mqtt_topic darf nicht leer sein")

    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    # Apply changes
    old_interval = app_settings["read_interval_minutes"]

    for key in ("camera_url", "read_interval_minutes", "mqtt_enabled", "mqtt_host", "mqtt_port", "mqtt_username", "mqtt_password", "mqtt_topic"):
        if key in data:
            # Don't overwrite password with masked value
            if key == "mqtt_password" and data[key] == "••••••••":
                continue
            app_settings[key] = data[key]

    # Persist
    save_settings(app_settings)
    logger.info(f"Settings updated: {app_settings}")

    # Reschedule if interval changed
    if app_settings["read_interval_minutes"] != old_interval:
        reschedule_readings()

    return jsonify({"status": "ok", "settings": app_settings})


@app.route("/api/mqtt/test", methods=["POST"])
def test_mqtt():
    """Test MQTT broker connection."""
    data = request.get_json()
    host = data.get("mqtt_host", app_settings.get("mqtt_host", "core-mosquitto"))
    port = data.get("mqtt_port", app_settings.get("mqtt_port", 1883))
    username = data.get("mqtt_username", "")
    password = data.get("mqtt_password", "")

    # If password is masked, use the stored one
    if password == "••••••••":
        password = app_settings.get("mqtt_password", "")

    try:
        import paho.mqtt.client as mqtt_client

        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        if username:
            client.username_pw_set(username, password)

        client.connect(host, port, keepalive=5)
        client.disconnect()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ─── Camera Control ────────────────────────────────────────────────────────────

CAMERA_SETTINGS_FILE = os.path.join(CONFIG_DIR, "camera_settings.json")

DEFAULT_CAMERA_SETTINGS = {
    "led_intensity": 50,
    "led_delay_ms": 500,
    "brightness": 0,
    "contrast": 0,
    "saturation": 0,
    "special_effect": "none",
    "ae_level": 0,
    "agc_gain_ceiling": "2x",
    "wb_mode": "auto",
    "horizontal_mirror": False,
    "vertical_flip": True,
    "resolution": "800x600",
    "jpeg_quality": 10,
    "rotation": 0,
}


def load_camera_settings() -> dict:
    """Load camera settings from file."""
    settings = DEFAULT_CAMERA_SETTINGS.copy()
    if os.path.exists(CAMERA_SETTINGS_FILE):
        try:
            with open(CAMERA_SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_camera_settings(settings: dict):
    """Persist camera settings."""
    os.makedirs(os.path.dirname(CAMERA_SETTINGS_FILE), exist_ok=True)
    with open(CAMERA_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def apply_camera_settings_to_esp(settings: dict) -> dict:
    """Apply camera settings to ESP32-CAM via its REST API."""
    import requests as req

    base_url = app_settings["camera_url"].rsplit("/", 1)[0]  # e.g. http://192.168.1.50:8080
    # Derive the ESPHome webserver base (port 80)
    esphome_base = base_url.split(":8080")[0]  # e.g. http://192.168.1.50

    results = {}

    # ─── Camera image settings via /control endpoint ───────────────────────────
    cam_control_url = esphome_base + "/control"
    plain_mappings = {
        "brightness": settings.get("brightness", 0),
        "contrast": settings.get("contrast", 0),
        "saturation": settings.get("saturation", 0),
        "hmirror": 1 if settings.get("horizontal_mirror") else 0,
        "vflip": 1 if settings.get("vertical_flip") else 0,
        "quality": settings.get("jpeg_quality", 10),
        "special_effect": ["none", "negative", "grayscale", "red_tint",
                           "green_tint", "blue_tint", "sepia"].index(
            settings.get("special_effect", "none")
        ),
        "ae_level": settings.get("ae_level", 0),
    }

    for var, val in plain_mappings.items():
        try:
            resp = req.get(
                cam_control_url, params={"var": var, "val": val}, timeout=3
            )
            results[var] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
        except Exception:
            results[var] = "unreachable"

    # ─── LED via ESPHome light entity ──────────────────────────────────────────
    led_intensity = settings.get("led_intensity", 0)
    try:
        if led_intensity > 0:
            # ESPHome expects brightness 0-255
            brightness = int(led_intensity * 255 / 100)
            resp = req.post(
                f"{esphome_base}/light/beleuchtung/turn_on",
                json={"brightness": brightness},
                timeout=3,
            )
            results["led"] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
        else:
            resp = req.post(
                f"{esphome_base}/light/beleuchtung/turn_off",
                timeout=3,
            )
            results["led"] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
    except Exception:
        results["led"] = "unreachable"

    return results


@app.route("/api/camera/settings", methods=["GET"])
def get_camera_settings():
    """Get current camera settings."""
    settings = load_camera_settings()
    return jsonify(settings)


@app.route("/api/camera/settings", methods=["POST"])
def update_camera_settings():
    """Update camera settings and apply to ESP32."""
    data = request.get_json()
    settings = load_camera_settings()

    # Validate ranges
    errors = []
    if "brightness" in data:
        if not (-2 <= data["brightness"] <= 2):
            errors.append("brightness muss zwischen -2 und 2 liegen")
    if "contrast" in data:
        if not (-2 <= data["contrast"] <= 2):
            errors.append("contrast muss zwischen -2 und 2 liegen")
    if "saturation" in data:
        if not (-2 <= data["saturation"] <= 2):
            errors.append("saturation muss zwischen -2 und 2 liegen")
    if "ae_level" in data:
        if not (-2 <= data["ae_level"] <= 2):
            errors.append("ae_level muss zwischen -2 und 2 liegen")
    if "led_intensity" in data:
        if not (0 <= data["led_intensity"] <= 100):
            errors.append("led_intensity muss zwischen 0 und 100 liegen")
    if "led_delay_ms" in data:
        if not (0 <= data["led_delay_ms"] <= 5000):
            errors.append("led_delay_ms muss zwischen 0 und 5000 liegen")
    if "jpeg_quality" in data:
        if not (6 <= data["jpeg_quality"] <= 63):
            errors.append("jpeg_quality muss zwischen 6 und 63 liegen")
    if "rotation" in data:
        if not (0 <= data["rotation"] <= 359):
            errors.append("rotation muss zwischen 0 und 359 liegen")

    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    # Apply valid fields
    valid_keys = list(DEFAULT_CAMERA_SETTINGS.keys())
    for key in valid_keys:
        if key in data:
            settings[key] = data[key]

    save_camera_settings(settings)

    # Try to apply to ESP32
    apply_results = apply_camera_settings_to_esp(settings)

    logger.info(f"Camera settings updated: {settings}")
    return jsonify({
        "status": "ok",
        "settings": settings,
        "apply_results": apply_results,
    })


@app.route("/api/camera/apply", methods=["POST"])
def apply_camera_settings():
    """Re-apply saved camera settings to ESP32 (e.g. after reboot)."""
    settings = load_camera_settings()
    apply_results = apply_camera_settings_to_esp(settings)
    return jsonify({"status": "ok", "apply_results": apply_results})


# ─── Reading Logic ─────────────────────────────────────────────────────────────


def perform_reading():
    """Perform a meter reading and report to HA."""
    result = engine.read_meter(app_settings["camera_url"])

    if result.get("success"):
        value = result["value"]
        logger.info(f"Meter reading: {value}")

        # Report to Home Assistant
        report_to_ha(value)

        # Report via MQTT if enabled
        if app_settings["mqtt_enabled"]:
            report_to_mqtt(value)
    else:
        logger.warning(f"Reading failed: {result.get('error')}")

    return result


def report_to_ha(value):
    """Report reading to Home Assistant via REST API."""
    if not SUPERVISOR_TOKEN:
        logger.info(f"No SUPERVISOR_TOKEN set, skipping HA report (value: {value})")
        return

    import requests

    try:
        url = "http://supervisor/core/api/states/sensor.meter_reader_water"
        headers = {
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "state": str(value),
            "attributes": {
                "unit_of_measurement": "m³",
                "device_class": "water",
                "state_class": "total_increasing",
                "friendly_name": "Wasserzähler",
                "last_updated": datetime.now().isoformat(),
            },
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            logger.info(f"Reported to HA: {value} m³")
        else:
            logger.error(f"HA API error: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"Failed to report to HA: {e}")


def report_to_mqtt(value):
    """Report reading via MQTT."""
    try:
        import paho.mqtt.publish as publish

        auth = None
        if app_settings.get("mqtt_username"):
            auth = {
                "username": app_settings["mqtt_username"],
                "password": app_settings.get("mqtt_password", ""),
            }

        publish.single(
            app_settings["mqtt_topic"],
            payload=str(value),
            hostname=app_settings.get("mqtt_host", "core-mosquitto"),
            port=app_settings.get("mqtt_port", 1883),
            auth=auth,
        )
        logger.info(f"Published to MQTT: {app_settings['mqtt_topic']} = {value}")
    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")


# ─── Scheduler ─────────────────────────────────────────────────────────────────


def reschedule_readings():
    """Clear and re-create the scheduled job with current interval."""
    schedule.clear()
    schedule.every(app_settings["read_interval_minutes"]).minutes.do(perform_reading)
    logger.info(f"Scheduler updated: reading every {app_settings['read_interval_minutes']} minutes")


def run_scheduler():
    """Background thread for scheduled readings."""
    schedule.every(app_settings["read_interval_minutes"]).minutes.do(perform_reading)
    logger.info(f"Scheduler started: reading every {app_settings['read_interval_minutes']} minutes")

    while True:
        schedule.run_pending()
        time.sleep(10)


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Meter Reader Addon starting...")

    # Start scheduler in background
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Start Flask (ingress uses port 5000)
    app.run(host="0.0.0.0", port=5000, debug=False)
