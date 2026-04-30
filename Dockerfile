FROM ghcr.io/home-assistant/aarch64-base:latest

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-pillow \
    py3-requests \
    py3-flask \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    build-base \
    python3-dev

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    opencv-python-headless==4.9.0.80 \
    tflite-runtime==2.14.0 \
    flask==3.0.* \
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
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
