FROM ghcr.io/home-assistant/aarch64-base:latest

# Install Python and dependencies via Alpine packages (pre-compiled, fast)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-pillow \
    py3-requests \
    py3-flask \
    py3-opencv \
    jpeg-dev \
    zlib-dev

# Install remaining Python packages
# Note: tflite-runtime is not available for Alpine/musl/aarch64
# We use OpenCV's DNN module to load TFLite models instead
RUN pip3 install --no-cache-dir --break-system-packages \
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
    io.hass.version="1.0.5" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"
