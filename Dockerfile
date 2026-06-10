FROM ghcr.io/home-assistant/base:3.21

# System-Abhängigkeiten (py3-opencv aus Alpine = vorgebaut, kein Compile nötig)
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

# Nur kleine Python-Pakete die kein nativen Build brauchen
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
    io.hass.version="2.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
