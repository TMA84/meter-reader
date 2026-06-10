FROM ghcr.io/home-assistant/base:3.21

# System-Abhängigkeiten
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-pillow \
    py3-requests \
    py3-flask \
    py3-opencv \
    jpeg-dev \
    zlib-dev \
    bash \
    wget

# Alpine's py3-opencv hat eine ungültige dist-info ("python-4.10.0") die pip
# zum Absturz bringt. Die dist-info umbenennen damit pip sie ignoriert.
RUN find /usr/lib/python3* -name "opencv*.dist-info" -type d \
    | xargs -I{} mv {} {}.disabled 2>/dev/null || true

# Jetzt können pip-Pakete normal installiert werden
RUN pip3 install --no-cache-dir --break-system-packages \
    paho-mqtt==2.1.* \
    schedule==1.2.*

# TFLite-Modell direkt beim Build herunterladen
RUN wget -q --timeout=60 \
    -O /opt/meter-reader/models/dig-class11.tflite \
    "https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/neuralnets/dig-class11/dig-class11-v2.3.tflite" \
    || wget -q --timeout=60 \
    -O /opt/meter-reader/models/dig-class11.tflite \
    "https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/neuralnets/dig-class11/dig-class11-v2.2.tflite"

# Copy application
COPY rootfs /

# Copy web frontend
COPY web /opt/meter-reader/web

RUN chmod a+x /run.sh

LABEL \
    io.hass.version="2.0.4" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
