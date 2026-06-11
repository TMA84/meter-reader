"""Meter Engine - Image capture, ROI extraction, and digit recognition."""

import json
import logging
import os
import threading
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

logger = logging.getLogger(__name__)


class MeterEngine:
    """Handles image capture, preprocessing, and digit recognition."""

    def __init__(self, config_path: str, models_path: str, data_path: str):
        self.config_path = config_path
        self.models_path = models_path
        self.data_path = data_path
        self.start_time = time.time()
        self.last_reading = None
        self.last_read_time = None
        self.interpreter = None  # ai-edge-litert Interpreter
        self.input_details = None
        self._snapshot_lock = threading.Lock()
        self.output_details = None

        self._load_model()
        self._load_config()

    def _load_model(self):
        """Load TFLite model via ai-edge-litert (supports TFL3 format)."""
        model_path = os.path.join(self.models_path, "dig-class11.tflite")
        if not os.path.exists(model_path):
            logger.warning(f"Modell nicht gefunden: {model_path}")
            return

        try:
            from ai_edge_litert.interpreter import Interpreter
            self.interpreter = Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            shape = self.input_details[0]['shape']
            logger.info(f"TFLite-Modell geladen: {model_path} (Input: {shape})")
        except Exception as e:
            logger.error(f"Modell konnte nicht geladen werden: {e}")
            self.interpreter = None

    def _load_config(self):
        """Load meter configuration."""
        try:
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = {"meters": [], "version": 1}
            self._save_config_to_disk()

    def _save_config_to_disk(self):
        """Write config to disk."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_config(self) -> dict:
        """Return current configuration."""
        self._load_config()
        return self.config

    def save_config(self, config: dict):
        """Save new configuration."""
        self.config = config
        self._save_config_to_disk()
        logger.info("Configuration saved")

    def capture_snapshot(self, camera_url: str) -> str | None:
        """Capture a snapshot from the camera with optional LED control."""
        if not self._snapshot_lock.acquire(blocking=False):
            snapshot_path = os.path.join(self.data_path, "snapshots", "latest.jpg")
            return snapshot_path if os.path.exists(snapshot_path) else None

        cam_settings = self._get_camera_settings()
        led_intensity = cam_settings.get("led_intensity", 0)
        led_delay_ms = cam_settings.get("led_delay_ms", 500)
        esphome_base = self._get_esphome_base(camera_url)
        led_on = False

        try:
            # LED einschalten
            if led_intensity > 0 and esphome_base:
                brightness = int(led_intensity * 255 / 100)
                try:
                    requests.post(
                        f"{esphome_base}/light/Beleuchtung/turn_on?brightness={brightness}",
                        headers={"Content-Length": "0"},
                        timeout=3,
                    )
                    led_on = True
                    # Alte Frames aus dem Buffer wegwerfen (frame_buffer_count=2)
                    for _ in range(2):
                        try:
                            requests.get(camera_url, timeout=5, headers={"Connection": "close"})
                        except Exception:
                            pass
                    # Warten bis AEC die Belichtung angepasst hat
                    time.sleep(led_delay_ms / 1000.0)
                except Exception as e:
                    logger.warning(f"LED control failed (continuing without): {e}")

            # Snapshot aufnehmen
            resp = requests.get(camera_url, timeout=15, headers={"Connection": "close"})
            resp.raise_for_status()

            snapshot_path = os.path.join(self.data_path, "snapshots", "latest.jpg")
            os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
            with open(snapshot_path, "wb") as f:
                f.write(resp.content)

            # Rotation und Spiegelung anwenden
            h_mirror = cam_settings.get("horizontal_mirror", False)
            v_flip = cam_settings.get("vertical_flip", False)
            rotation = cam_settings.get("rotation", 0)
            if rotation != 0 or h_mirror or v_flip:
                img = cv2.imread(snapshot_path)
                if img is not None:
                    if h_mirror:
                        img = cv2.flip(img, 1)
                    if v_flip:
                        img = cv2.flip(img, 0)
                    if rotation != 0:
                        img = self._rotate_image(img, rotation)
                    cv2.imwrite(snapshot_path, img)

            return snapshot_path
        except Exception as e:
            logger.error(f"Snapshot capture failed: {e}")
            return None
        finally:
            # LED immer ausschalten - kurz warten damit letzter Frame vollständig belichtet
            if led_on and esphome_base:
                led_off_delay_ms = cam_settings.get("led_off_delay_ms", 300)
                time.sleep(led_off_delay_ms / 1000.0)
                try:
                    requests.post(
                        f"{esphome_base}/light/Beleuchtung/turn_off",
                        headers={"Content-Length": "0"},
                        timeout=3,
                    )
                except Exception:
                    pass
            self._snapshot_lock.release()

    def get_cached_snapshot(self) -> str | None:
        """Return path to last captured snapshot without triggering a new one."""
        path = os.path.join(self.data_path, "snapshots", "latest.jpg")
        return path if os.path.exists(path) else None

    def get_cached_annotated_snapshot(self) -> str | None:
        """Return path to last annotated snapshot without triggering a new one."""
        path = os.path.join(self.data_path, "snapshots", "annotated.jpg")
        return path if os.path.exists(path) else None

    def _get_esphome_base(self, camera_url: str) -> str | None:
        """Derive ESPHome webserver base URL (port 80) from camera URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(camera_url)
            # ESPHome webserver runs on port 80, camera snapshot on :8080
            return f"{parsed.scheme}://{parsed.hostname}"
        except Exception:
            return None

    def _get_camera_settings(self) -> dict:
        """Load camera settings from file."""
        cam_settings_path = os.path.join(
            os.path.dirname(self.config_path), "camera_settings.json"
        )
        if os.path.exists(cam_settings_path):
            try:
                with open(cam_settings_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"led_intensity": 0, "led_delay_ms": 500, "rotation": 0}

    def _rotate_image(self, img: np.ndarray, degrees: int) -> np.ndarray:
        """Rotate image by arbitrary degrees. Uses fast path for 90/180/270."""
        if degrees == 0:
            return img
        if degrees == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif degrees == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        elif degrees == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # Arbitrary rotation with border handling
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, -degrees, 1.0)

            # Calculate new bounding box size
            cos = abs(matrix[0, 0])
            sin = abs(matrix[0, 1])
            new_w = int(h * sin + w * cos)
            new_h = int(h * cos + w * sin)

            # Adjust the rotation matrix for the new center
            matrix[0, 2] += (new_w - w) / 2
            matrix[1, 2] += (new_h - h) / 2

            return cv2.warpAffine(img, matrix, (new_w, new_h),
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0))

    def capture_annotated_snapshot(self, camera_url: str) -> str | None:
        """Capture snapshot with ROI rectangles drawn."""
        snapshot_path = self.capture_snapshot(camera_url)
        if not snapshot_path:
            return None

        try:
            img = cv2.imread(snapshot_path)
            meters = self.config.get("meters", [])

            for meter in meters:
                rois = meter.get("rois", [])
                for roi in rois:
                    x = roi.get("x", 0)
                    y = roi.get("y", 0)
                    w = roi.get("w", 50)
                    h = roi.get("h", 50)
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            annotated_path = os.path.join(
                self.data_path, "snapshots", "annotated.jpg"
            )
            cv2.imwrite(annotated_path, img)
            return annotated_path
        except Exception as e:
            logger.error(f"Annotation failed: {e}")
            return snapshot_path

    def read_meter(self, camera_url: str) -> dict:
        """Perform a full meter reading."""
        if not self.interpreter:
            return {"success": False, "error": "Kein Modell geladen"}

        meters = self.config.get("meters", [])
        if not meters:
            return {"success": False, "error": "No meters configured"}

        # Capture image
        snapshot_path = self.capture_snapshot(camera_url)
        if not snapshot_path:
            return {"success": False, "error": "Could not capture image"}

        try:
            img = cv2.imread(snapshot_path)
            if img is None:
                return {"success": False, "error": "Could not read image"}

            # Process first configured meter
            meter = meters[0]
            rois = meter.get("rois", [])
            decimal_position = meter.get("decimal_position", 0)
            max_rate = meter.get("max_rate", 500)

            if not rois:
                return {"success": False, "error": "No ROIs configured"}

            # Extract and classify each digit
            digits = []
            for roi in rois:
                digit = self._classify_digit(img, roi)
                digits.append(digit)

            # Build value string
            value_str = ""
            for i, d in enumerate(digits):
                if d == 10:  # NaN class
                    value_str += "N"
                else:
                    value_str += str(d)
                if decimal_position > 0 and i == len(digits) - decimal_position - 1:
                    value_str += "."

            # Try to parse as float
            try:
                value = float(value_str.replace("N", ""))
            except ValueError:
                return {
                    "success": False,
                    "error": f"Could not parse value: {value_str}",
                    "raw": value_str,
                }

            # Plausibility check
            if self.last_reading is not None:
                diff = value - self.last_reading
                if diff < 0:
                    return {
                        "success": False,
                        "error": f"Value decreased: {value} < {self.last_reading}",
                        "raw": value_str,
                    }
                if diff > max_rate:
                    return {
                        "success": False,
                        "error": f"Rate too high: {diff} > {max_rate}",
                        "raw": value_str,
                    }

            # Success
            self.last_reading = value
            self.last_read_time = datetime.now().isoformat()

            # Save reading to log
            self._log_reading(value, value_str)

            return {
                "success": True,
                "value": value,
                "raw": value_str,
                "timestamp": self.last_read_time,
            }

        except Exception as e:
            logger.error(f"Reading failed: {e}")
            return {"success": False, "error": str(e)}

    def _classify_digit(self, img: np.ndarray, roi: dict) -> int:
        """Classify a single digit from the image using ai-edge-litert."""
        x = roi.get("x", 0)
        y = roi.get("y", 0)
        w = roi.get("w", 50)
        h = roi.get("h", 50)

        crop = img[y : y + h, x : x + w]

        # Modell-Input-Shape ermitteln: [1, H, W, C]
        shape = self.input_details[0]['shape']
        model_h, model_w, model_c = int(shape[1]), int(shape[2]), int(shape[3])

        if model_c == 1:
            crop_resized = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (model_w, model_h))
            input_data = crop_resized.reshape(1, model_h, model_w, 1)
        else:
            crop_resized = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), (model_w, model_h))
            input_data = crop_resized.reshape(1, model_h, model_w, model_c)

        # Normalisieren je nach Datentyp (float32 → [0,1], uint8 → unverändert)
        dtype = self.input_details[0]['dtype']
        if dtype == np.float32:
            input_data = input_data.astype(np.float32) / 255.0
        else:
            input_data = input_data.astype(dtype)

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])

        # Klasse 0-9 = Ziffern, 10 = NaN
        return int(np.argmax(output[0]))

    def _log_reading(self, value: float, raw: str):
        """Append reading to log file."""
        log_file = os.path.join(self.data_path, "logs", "readings.jsonl")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "raw": raw,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_readings(self, limit: int = 100) -> list:
        """Get recent readings from log."""
        log_file = os.path.join(self.data_path, "logs", "readings.jsonl")
        if not os.path.exists(log_file):
            return []

        readings = []
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        readings.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return readings[-limit:]

    def test_roi(self, camera_url: str, rois: list) -> dict:
        """Test ROI configuration and return recognized digits."""
        if not self.interpreter:
            return {"success": False, "error": "Kein Modell geladen"}

        snapshot_path = self.capture_snapshot(camera_url)
        if not snapshot_path:
            return {"success": False, "error": "Could not capture image"}

        img = cv2.imread(snapshot_path)
        if img is None:
            return {"success": False, "error": "Could not read image"}

        results = []
        for roi in rois:
            digit = self._classify_digit(img, roi)
            results.append({"roi": roi, "digit": digit if digit < 10 else "N"})

        return {"success": True, "results": results}

    def get_uptime(self) -> str:
        """Get addon uptime."""
        elapsed = int(time.time() - self.start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        return f"{hours}h {minutes}m"
