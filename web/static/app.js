/**
 * Meter Reader - Frontend Application
 */

// ─── State ────────────────────────────────────────────────────────────────────
let currentConfig = { meters: [], version: 1 };
let rois = [];

// Determine base path for API calls (ingress support)
// Works by detecting the path prefix from the current page URL
const BASE = window.location.pathname.replace(/\/$/, '');

function apiUrl(path) {
    return `${BASE}/api${path}`;
}

// ─── Navigation ───────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        // Update nav
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        // Show page
        const page = item.dataset.page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');

        // Load data for page
        if (page === 'history') loadHistory();
        if (page === 'configure') loadConfiguration();
        if (page === 'settings') loadSettings();
        if (page === 'camera') loadCameraSettings();
    });
});

// ─── Dashboard ────────────────────────────────────────────────────────────────
async function loadStatus() {
    try {
        const resp = await fetch(apiUrl('/status'));
        const data = await resp.json();

        document.getElementById('current-value').textContent =
            data.last_reading !== null ? data.last_reading.toFixed(3) : '--';
        document.getElementById('status-text').textContent =
            data.last_reading !== null ? 'Aktiv' : 'Warte auf erste Ablesung';
        document.getElementById('last-read-time').textContent =
            data.last_read_time ? `Letzte Ablesung: ${formatTime(data.last_read_time)}` : '';
        document.getElementById('uptime').textContent = data.uptime || '--';
    } catch (e) {
        console.error('Status load failed:', e);
    }
}

async function triggerReading() {
    try {
        showToast('Ablesung wird durchgeführt...', 'success');
        const resp = await fetch(apiUrl('/read'), { method: 'POST' });
        const data = await resp.json();

        if (data.success) {
            showToast(`Ablesung erfolgreich: ${data.value} m³`, 'success');
            loadStatus();
        } else {
            showToast(`Fehler: ${data.error}`, 'error');
        }
    } catch (e) {
        showToast('Verbindungsfehler', 'error');
    }
}

async function refreshSnapshot() {
    const img = document.getElementById('snapshot-img');
    img.src = apiUrl('/snapshot/annotated') + '?t=' + Date.now();
}

// ─── Configuration ────────────────────────────────────────────────────────────
async function loadConfiguration() {
    try {
        const resp = await fetch(apiUrl('/config'));
        currentConfig = await resp.json();

        const meter = currentConfig.meters?.[0] || {};
        document.getElementById('meter-name').value = meter.name || 'Wasserzähler';
        document.getElementById('decimal-position').value = meter.decimal_position ?? 3;
        document.getElementById('max-rate').value = meter.max_rate ?? 500;
        document.getElementById('initial-value').value = meter.initial_value || '';

        rois = meter.rois || [];
        renderRoiList();
    } catch (e) {
        console.error('Config load failed:', e);
    }
}

async function saveConfiguration() {
    const meter = {
        name: document.getElementById('meter-name').value,
        decimal_position: parseInt(document.getElementById('decimal-position').value),
        max_rate: parseInt(document.getElementById('max-rate').value),
        initial_value: parseFloat(document.getElementById('initial-value').value) || null,
        rois: rois,
    };

    currentConfig.meters = [meter];

    try {
        const resp = await fetch(apiUrl('/config'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentConfig),
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            showToast('Konfiguration gespeichert', 'success');
        } else {
            showToast('Fehler beim Speichern', 'error');
        }
    } catch (e) {
        showToast('Verbindungsfehler', 'error');
    }
}

function addRoi() {
    const index = rois.length;
    rois.push({ x: 50 + index * 60, y: 50, w: 50, h: 70 });
    renderRoiList();
    drawRoisOnCanvas();
}

function removeRoi(index) {
    rois.splice(index, 1);
    renderRoiList();
    drawRoisOnCanvas();
}

function updateRoi(index, field, value) {
    rois[index][field] = parseInt(value) || 0;
    drawRoisOnCanvas();
}

function renderRoiList() {
    const container = document.getElementById('roi-list');
    container.innerHTML = '';

    rois.forEach((roi, i) => {
        const entry = document.createElement('div');
        entry.className = 'roi-entry';
        entry.innerHTML = `
            <span class="roi-label">Ziffer ${i + 1}</span>
            <div class="roi-fields">
                <span>X:</span>
                <input type="number" value="${roi.x}" onchange="updateRoi(${i}, 'x', this.value)" />
                <span>Y:</span>
                <input type="number" value="${roi.y}" onchange="updateRoi(${i}, 'y', this.value)" />
                <span>B:</span>
                <input type="number" value="${roi.w}" onchange="updateRoi(${i}, 'w', this.value)" />
                <span>H:</span>
                <input type="number" value="${roi.h}" onchange="updateRoi(${i}, 'h', this.value)" />
            </div>
            <button class="btn btn-danger" onclick="removeRoi(${i})">✕</button>
        `;
        container.appendChild(entry);
    });
}

async function loadRoiImage() {
    const img = document.getElementById('roi-img');
    img.src = apiUrl('/snapshot') + '?t=' + Date.now();
    img.onload = () => {
        const canvas = document.getElementById('roi-canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.style.width = img.width + 'px';
        canvas.style.height = img.height + 'px';
        drawRoisOnCanvas();
    };
}

function drawRoisOnCanvas() {
    const canvas = document.getElementById('roi-canvas');
    const ctx = canvas.getContext('2d');
    if (!canvas.width) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    rois.forEach((roi, i) => {
        // Rectangle
        ctx.strokeStyle = '#4fd1c5';
        ctx.lineWidth = 2;
        ctx.strokeRect(roi.x, roi.y, roi.w, roi.h);

        // Label
        ctx.fillStyle = '#4fd1c5';
        ctx.font = '14px sans-serif';
        ctx.fillText(`${i + 1}`, roi.x + 2, roi.y - 4);
    });
}

async function testRois() {
    try {
        const resp = await fetch(apiUrl('/roi/test'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rois }),
        });
        const data = await resp.json();

        if (data.success) {
            const container = document.getElementById('test-digits');
            container.innerHTML = '';
            data.results.forEach(r => {
                const div = document.createElement('div');
                div.className = 'digit' + (r.digit === 'N' ? ' nan' : '');
                div.textContent = r.digit;
                container.appendChild(div);
            });
            document.getElementById('roi-test-result').classList.remove('hidden');
            showToast('ROI-Test abgeschlossen', 'success');
        } else {
            showToast(`Test fehlgeschlagen: ${data.error}`, 'error');
        }
    } catch (e) {
        showToast('Verbindungsfehler', 'error');
    }
}

// ─── History ──────────────────────────────────────────────────────────────────
async function loadHistory() {
    try {
        const resp = await fetch(apiUrl('/readings?limit=200'));
        const readings = await resp.json();

        // Render table
        const tbody = document.getElementById('readings-tbody');
        tbody.innerHTML = '';

        // Show newest first
        const reversed = [...readings].reverse();
        reversed.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${formatTime(r.timestamp)}</td>
                <td>${r.value.toFixed(3)}</td>
                <td>${r.raw}</td>
            `;
            tbody.appendChild(tr);
        });

        // Simple chart (SVG-based, no external dependency)
        renderChart(readings);
    } catch (e) {
        console.error('History load failed:', e);
    }
}

function renderChart(readings) {
    const canvas = document.getElementById('history-chart');
    const ctx = canvas.getContext('2d');

    // Set canvas size
    const container = canvas.parentElement;
    canvas.width = container.clientWidth - 48;
    canvas.height = 200;

    if (readings.length < 2) {
        ctx.fillStyle = '#718096';
        ctx.font = '14px sans-serif';
        ctx.fillText('Noch nicht genug Daten für ein Diagramm', 20, 100);
        return;
    }

    const values = readings.map(r => r.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const padding = { top: 20, right: 20, bottom: 30, left: 60 };
    const w = canvas.width - padding.left - padding.right;
    const h = canvas.height - padding.top - padding.bottom;

    // Background
    ctx.fillStyle = '#1f2b47';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid lines
    ctx.strokeStyle = '#2d3748';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (h / 4) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + w, y);
        ctx.stroke();

        // Y-axis labels
        const val = max - (range / 4) * i;
        ctx.fillStyle = '#718096';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(val.toFixed(2), padding.left - 8, y + 4);
    }

    // Line chart
    ctx.beginPath();
    ctx.strokeStyle = '#4fd1c5';
    ctx.lineWidth = 2;

    values.forEach((v, i) => {
        const x = padding.left + (i / (values.length - 1)) * w;
        const y = padding.top + h - ((v - min) / range) * h;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + h);
    gradient.addColorStop(0, 'rgba(79, 209, 197, 0.3)');
    gradient.addColorStop(1, 'rgba(79, 209, 197, 0)');

    ctx.lineTo(padding.left + w, padding.top + h);
    ctx.lineTo(padding.left, padding.top + h);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
}

// ─── Camera Settings ──────────────────────────────────────────────────────────
async function loadCameraSettings() {
    refreshCameraPreview();
    try {
        const resp = await fetch(apiUrl('/camera/settings'));
        const settings = await resp.json();

        setSlider('cam-led-intensity', settings.led_intensity ?? 50);
        setSlider('cam-led-delay', settings.led_delay_ms ?? 500);
        setSlider('cam-brightness', settings.brightness ?? 0);
        setSlider('cam-contrast', settings.contrast ?? 0);
        setSlider('cam-saturation', settings.saturation ?? 0);
        setSlider('cam-ae-level', settings.ae_level ?? 0);

        document.getElementById('cam-special-effect').value = settings.special_effect || 'none';
        document.getElementById('cam-wb-mode').value = settings.wb_mode || 'auto';
        document.getElementById('cam-resolution').value = settings.resolution || '800x600';
        document.getElementById('cam-jpeg-quality').value = settings.jpeg_quality ?? 10;
        setSlider('cam-rotation', settings.rotation ?? 0);
        document.getElementById('cam-hmirror').checked = settings.horizontal_mirror || false;
        document.getElementById('cam-vflip').checked = settings.vertical_flip ?? true;
    } catch (e) {
        console.error('Camera settings load failed:', e);
    }
}

async function saveCameraSettings() {
    const settings = {
        led_intensity: parseInt(document.getElementById('cam-led-intensity').value),
        led_delay_ms: parseInt(document.getElementById('cam-led-delay').value),
        brightness: parseInt(document.getElementById('cam-brightness').value),
        contrast: parseInt(document.getElementById('cam-contrast').value),
        saturation: parseInt(document.getElementById('cam-saturation').value),
        ae_level: parseInt(document.getElementById('cam-ae-level').value),
        special_effect: document.getElementById('cam-special-effect').value,
        wb_mode: document.getElementById('cam-wb-mode').value,
        resolution: document.getElementById('cam-resolution').value,
        jpeg_quality: parseInt(document.getElementById('cam-jpeg-quality').value),
        rotation: parseInt(document.getElementById('cam-rotation').value),
        horizontal_mirror: document.getElementById('cam-hmirror').checked,
        vertical_flip: document.getElementById('cam-vflip').checked,
    };

    try {
        const resp = await fetch(apiUrl('/camera/settings'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            showToast('Kamera-Einstellungen gespeichert & angewendet', 'success');
            // Refresh preview after a short delay to see the effect
            setTimeout(refreshCameraPreview, 1000);
        } else {
            const msg = data.errors ? data.errors.join(', ') : 'Unbekannter Fehler';
            showToast(`Fehler: ${msg}`, 'error');
        }
    } catch (e) {
        showToast('Verbindungsfehler', 'error');
    }
}

function refreshCameraPreview() {
    const img = document.getElementById('camera-preview-img');
    img.src = apiUrl('/snapshot') + '?t=' + Date.now();
}

function setSlider(id, value) {
    const slider = document.getElementById(id);
    slider.value = value;
    document.getElementById(id + '-val').textContent = value;
}

function updateSliderLabel(input) {
    document.getElementById(input.id + '-val').textContent = input.value;
}

// ─── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
    try {
        const resp = await fetch(apiUrl('/settings'));
        const settings = await resp.json();

        document.getElementById('setting-camera-url').value = settings.camera_url || '';
        document.getElementById('setting-interval').value = settings.read_interval_minutes || 5;
        document.getElementById('setting-mqtt-enabled').checked = settings.mqtt_enabled || false;
        document.getElementById('setting-mqtt-host').value = settings.mqtt_host || '';
        document.getElementById('setting-mqtt-port').value = settings.mqtt_port || 1883;
        document.getElementById('setting-mqtt-username').value = settings.mqtt_username || '';
        document.getElementById('setting-mqtt-password').value = settings.mqtt_password || '';
        document.getElementById('setting-mqtt-password').placeholder =
            settings.mqtt_password === '••••••••' ? '(gespeichert)' : '(optional)';
        document.getElementById('setting-mqtt-topic').value = settings.mqtt_topic || '';

        // Info section
        document.getElementById('settings-source').textContent =
            settings._from_file ? 'Gespeicherte Einstellungen' : 'Addon-Konfiguration / Umgebung';
    } catch (e) {
        console.error('Settings load failed:', e);
    }
}

async function saveSettings() {
    const settings = {
        camera_url: document.getElementById('setting-camera-url').value.trim(),
        read_interval_minutes: parseInt(document.getElementById('setting-interval').value),
        mqtt_enabled: document.getElementById('setting-mqtt-enabled').checked,
        mqtt_host: document.getElementById('setting-mqtt-host').value.trim(),
        mqtt_port: parseInt(document.getElementById('setting-mqtt-port').value),
        mqtt_username: document.getElementById('setting-mqtt-username').value.trim(),
        mqtt_password: document.getElementById('setting-mqtt-password').value,
        mqtt_topic: document.getElementById('setting-mqtt-topic').value.trim(),
    };

    try {
        const resp = await fetch(apiUrl('/settings'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            showToast('Einstellungen gespeichert', 'success');
        } else {
            const msg = data.errors ? data.errors.join(', ') : 'Unbekannter Fehler';
            showToast(`Fehler: ${msg}`, 'error');
        }
    } catch (e) {
        showToast('Verbindungsfehler', 'error');
    }
}

async function testCameraConnection() {
    const indicator = document.getElementById('camera-test-result');
    indicator.textContent = 'Teste...';
    indicator.className = 'test-indicator';

    try {
        const resp = await fetch(apiUrl('/snapshot'));
        if (resp.ok) {
            indicator.textContent = '✓ Verbindung erfolgreich';
            indicator.className = 'test-indicator success';
        } else {
            indicator.textContent = '✗ Keine Verbindung';
            indicator.className = 'test-indicator error';
        }
    } catch (e) {
        indicator.textContent = '✗ Fehler: ' + e.message;
        indicator.className = 'test-indicator error';
    }
}

async function testMqttConnection() {
    const indicator = document.getElementById('mqtt-test-result');
    indicator.textContent = 'Teste...';
    indicator.className = 'test-indicator';

    const mqttSettings = {
        mqtt_host: document.getElementById('setting-mqtt-host').value.trim(),
        mqtt_port: parseInt(document.getElementById('setting-mqtt-port').value),
        mqtt_username: document.getElementById('setting-mqtt-username').value.trim(),
        mqtt_password: document.getElementById('setting-mqtt-password').value,
    };

    try {
        const resp = await fetch(apiUrl('/mqtt/test'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mqttSettings),
        });
        const data = await resp.json();

        if (data.success) {
            indicator.textContent = '✓ Verbindung erfolgreich';
            indicator.className = 'test-indicator success';
        } else {
            indicator.textContent = '✗ ' + (data.error || 'Verbindung fehlgeschlagen');
            indicator.className = 'test-indicator error';
        }
    } catch (e) {
        indicator.textContent = '✗ Fehler: ' + e.message;
        indicator.className = 'test-indicator error';
    }
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function formatTime(isoString) {
    if (!isoString) return '--';
    const d = new Date(isoString);
    return d.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

// ─── Init ─────────────────────────────────────────────────────────────────────
loadStatus();
refreshSnapshot();

// Auto-refresh status every 30s
setInterval(loadStatus, 30000);
