ARG BUILD_FROM
FROM $BUILD_FROM

# System-Abhängigkeiten (Debian bookworm = glibc, manylinux-Wheels funktionieren)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-numpy \
    python3-pil \
    python3-requests \
    python3-flask \
    python3-opencv \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Python-Pakete (ai-edge-litert benötigt glibc/manylinux, daher Debian statt Alpine)
RUN pip3 install --no-cache-dir --break-system-packages \
    ai-edge-litert==2.1.5 \
    paho-mqtt==2.1.* \
    schedule==1.2.*

# Copy application
COPY rootfs /

# Modell aus dem Repo
RUN mkdir -p /opt/meter-reader/models
COPY models/dig-class11.tflite /opt/meter-reader/models/dig-class11.tflite

# Copy web frontend
COPY web /opt/meter-reader/web

RUN chmod a+x /run.sh

LABEL \
    io.hass.version="2.1.2" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
