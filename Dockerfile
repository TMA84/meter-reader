FROM ghcr.io/home-assistant/base:3.21

# System-Abhängigkeiten
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-pillow \
    py3-requests \
    py3-flask \
    jpeg-dev \
    zlib-dev \
    bash \
    wget \
    # OpenCV aus source braucht diese Build-Deps nicht –
    # wir installieren opencv-python via pip (enthält 4.9+)
    libstdc++ \
    libgomp

# opencv-python-headless bringt OpenCV 4.9+ mit TFLite-Support (readNetFromTFLite)
# tflite-runtime als Fallback für direkten Interpreter-Zugriff
RUN pip3 install --no-cache-dir --break-system-packages \
    opencv-python-headless==4.9.* \
    paho-mqtt==2.1.* \
    schedule==1.2.*

# Copy application
COPY rootfs /

# Copy TFLite models
COPY models /opt/meter-reader/models

# Copy web frontend
COPY web /opt/meter-reader/web

RUN chmod a+x /run.sh

LABEL \
    io.hass.version="2.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
