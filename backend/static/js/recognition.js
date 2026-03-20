let stream = null;
let reconnectAttempts = 0;
let isProcessing = false;
let recentCaptures = [];
let currentAction = 'time_in';

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const placeholder = document.getElementById('video-placeholder');
const toggleBtn = document.getElementById('toggle-camera');
const cameraSelect = document.getElementById('camera-select');
const captureBtn = document.getElementById('capture-btn');
const overlay = document.getElementById('recognition-overlay');
const overlayIcon = document.getElementById('overlay-icon');
const overlayMessage = document.getElementById('overlay-message');
const overlayDetails = document.getElementById('overlay-details');
const livenessIndicator = document.getElementById('liveness-indicator');
const nameOverlay = document.getElementById('name-overlay');

const MAX_RECONNECT_ATTEMPTS = 5;
const LIVENESS_CHECK_ENABLED = false;
const MAX_RECENT_CAPTURES = 10;

async function getCameras() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        showPlaceholder('Camera API not available', 'Your browser doesn\'t support camera access or you\'re not using HTTPS');
        toggleBtn.disabled = true;
        cameraSelect.disabled = true;
        return;
    }

    try {
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tempStream.getTracks().forEach(track => track.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');

        if (videoDevices.length === 0) {
            showPlaceholder('No camera detected', 'Connect a webcam to use face recognition');
            toggleBtn.disabled = true;
            cameraSelect.innerHTML = '<option value="">No cameras found</option>';
            return;
        }

        cameraSelect.innerHTML = '<option value="">Select Camera</option>';
        videoDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Camera ${index + 1}`;
            cameraSelect.appendChild(option);
        });

        if (videoDevices.length === 1) {
            cameraSelect.value = videoDevices[0].deviceId;
        }
        showPlaceholder('Camera Ready', `${videoDevices.length} camera(s) detected - Click "Start Camera"`);
    } catch (error) {
        console.error('Error accessing cameras:', error);
        handleCameraError(error);
    }
}

function handleCameraError(error) {
    let message = 'Camera access denied';
    let subtitle = 'Please allow camera access in your browser settings';

    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        message = 'No camera found';
        subtitle = 'Connect a webcam to continue';
    } else if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        message = 'Camera permission denied';
        subtitle = 'Click the camera icon in your browser address bar to allow access';
    } else if (error.name === 'NotReadableError') {
        message = 'Camera is in use';
        subtitle = 'Close other apps using the camera and try again';
    }

    showPlaceholder(message, subtitle);
    toggleBtn.disabled = true;
    cameraSelect.disabled = true;
}

function showPlaceholder(title, subtitle) {
    placeholder.innerHTML = `
        <div class="placeholder-icon">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
            </svg>
        </div>
        <p class="placeholder-title">${title}</p>
        <p class="placeholder-subtitle">${subtitle}</p>
    `;
}

async function startCamera() {
    const deviceId = cameraSelect.value;

    if (!deviceId) {
        showToast('Please select a camera from the dropdown', 'warning');
        return;
    }

    toggleBtn.disabled = true;
    toggleBtn.textContent = 'Starting...';
    showPlaceholder('Requesting camera access...', '');

    try {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }

        const constraints = {
            video: {
                deviceId: { exact: deviceId },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;

        await new Promise((resolve, reject) => {
            video.onloadedmetadata = resolve;
            video.onerror = () => reject(new Error('Video failed to load'));
            setTimeout(() => reject(new Error('Video load timeout')), 5000);
        });

        await video.play();

        video.style.display = 'block';
        placeholder.style.display = 'none';
        toggleBtn.textContent = 'Stop Camera';
        toggleBtn.disabled = false;
        captureBtn.disabled = false;

        reconnectAttempts = 0;
        monitorCameraConnection();

        showToast('Camera started - Click "Capture & Recognize" when ready', 'success');
    } catch (error) {
        console.error('Error starting camera:', error);
        toggleBtn.textContent = 'Start Camera';
        toggleBtn.disabled = false;
        handleCameraStartError(error);
    }
}

function handleCameraStartError(error) {
    let message = 'Failed to start camera';

    if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        message = 'Camera is being used by another application';
    } else if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        message = 'Camera permission denied';
    } else if (error.name === 'NotFoundError') {
        message = 'Camera not found';
    } else if (error.name === 'OverconstrainedError') {
        tryBasicCamera();
        return;
    }

    showPlaceholder(message, 'Please resolve the issue and try again');
    showToast(message, 'error');
}

async function tryBasicCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        await video.play();
        video.style.display = 'block';
        placeholder.style.display = 'none';
        toggleBtn.textContent = 'Stop Camera';
        captureBtn.disabled = false;
        showToast('Camera started in basic mode', 'success');
    } catch (e) {
        showPlaceholder('Could not start camera', e.message);
        showToast('Camera error: ' + e.message, 'error');
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }

    video.srcObject = null;
    video.style.display = 'none';
    placeholder.style.display = 'flex';
    overlay.style.display = 'none';
    livenessIndicator.style.display = 'none';
    toggleBtn.textContent = 'Start Camera';
    captureBtn.disabled = true;

    showPlaceholder('Camera Stopped', 'Click "Start Camera" to resume');
}

async function performRecognition() {
    if (!stream || isProcessing) {
        showToast('Please wait, processing...', 'warning');
        return;
    }

    isProcessing = true;
    captureBtn.disabled = true;

    try {
        if (LIVENESS_CHECK_ENABLED) {
            livenessIndicator.style.display = 'flex';
            const livenessResult = await performLivenessCheck();
            livenessIndicator.style.display = 'none';

            if (!livenessResult.passed) {
                showOverlay('Please look at the camera', 'Live person detection required', 'warning');
                isProcessing = false;
                return;
            }
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        const imageBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));

        const formData = new FormData();
        formData.append('face_image', imageBlob, `snapshot_${Date.now()}.jpg`);
        formData.append('action', currentAction);

        const response = await fetch('/api/recognition/identify', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        displayRecognitionResult(result, currentAction);

    } catch (error) {
        console.error('Recognition error:', error);
        showOverlay('Recognition failed', 'Please try again', 'error');
    } finally {
        isProcessing = false;
        captureBtn.disabled = false;
    }
}

async function performLivenessCheck() {
    return new Promise((resolve) => {
        const checkDuration = 500;
        let frameCount = 0;
        let brightnessChanges = 0;
        let lastBrightness = 0;

        const tempCanvas = document.createElement('canvas');
        const interval = setInterval(() => {
            if (!video.videoWidth) {
                resolve({ passed: false, reason: 'No video' });
                clearInterval(interval);
                return;
            }

            tempCanvas.width = video.videoWidth / 4;
            tempCanvas.height = video.videoHeight / 4;
            const ctx = tempCanvas.getContext('2d');
            ctx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);

            const imageData = ctx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
            const data = imageData.data;
            let totalBrightness = 0;

            for (let i = 0; i < data.length; i += 4) {
                totalBrightness += (data[i] + data[i + 1] + data[i + 2]) / 3;
            }

            const avgBrightness = totalBrightness / (data.length / 4);

            if (frameCount > 0 && Math.abs(avgBrightness - lastBrightness) > 2) {
                brightnessChanges++;
            }

            lastBrightness = avgBrightness;
            frameCount++;

            if (frameCount >= 3) {
                clearInterval(interval);
                resolve({ passed: brightnessChanges >= 1, reason: 'Liveness check' });
            }
        }, checkDuration / 3);
    });
}

function displayRecognitionResult(result, action) {
    const actionLabel = action === 'time_in' ? 'Time In' : 'Time Out';

    if (result.recognized) {
        const confidence = (result.confidence * 100).toFixed(1);
        showOverlay(
            `Welcome, ${result.name}`,
            `${actionLabel} recorded | Confidence: ${confidence}%`,
            'success'
        );
        showToast(`${result.name} - ${actionLabel} recorded`, 'success');

        if (nameOverlay) {
            nameOverlay.textContent = `NAME: ${result.name}`;
            nameOverlay.style.display = 'block';
        }
    } else {
        const confidence = (result.confidence * 100).toFixed(1);
        showOverlay(
            'Face not recognized',
            `Confidence: ${confidence}% | ${result.message}`,
            'error'
        );
        showToast('Face not recognized', 'error');

        if (nameOverlay) {
            nameOverlay.style.display = 'none';
        }
    }

    addRecentCapture(result, action);

    setTimeout(() => {
        hideOverlay();
        if (nameOverlay) {
            nameOverlay.style.display = 'none';
        }
    }, 4000);
}

function addRecentCapture(result, action) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const screenshotUrl = canvas.toDataURL('image/jpeg', 0.7);
    const now = new Date();
    const confidence = (result.confidence * 100).toFixed(1);

    const capture = {
        id: Date.now(),
        name: result.name || 'Unrecognized',
        recognized: result.recognized,
        action: action,
        time: now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }),
        confidence: confidence,
        image: screenshotUrl
    };

    recentCaptures.unshift(capture);

    if (recentCaptures.length > MAX_RECENT_CAPTURES) {
        recentCaptures = recentCaptures.slice(0, MAX_RECENT_CAPTURES);
    }

    updateRecentCapturesList();
}

function updateRecentCapturesList() {
    const capturesList = document.getElementById('recent-captures-list');

    if (recentCaptures.length === 0) {
        capturesList.innerHTML = '<div class="empty-captures"><p>No captures yet</p></div>';
        return;
    }

    capturesList.innerHTML = recentCaptures.map((capture, index) => `
        <div class="capture-item">
            <div class="capture-item-avatar">
                <img src="${capture.image}" alt="${capture.name}">
            </div>
            <div class="capture-item-content">
                <div class="capture-item-title">CAPTURE ${index + 1}:</div>
                <div class="capture-item-name ${capture.recognized ? '' : 'unrecognized'}">
                    ${capture.recognized ? 'Recognized: ' + capture.name : 'Unrecognized'}
                </div>
                <div class="capture-item-time">Time: ${capture.time}</div>
                <span class="capture-item-badge ${capture.recognized ? 'recognized' : 'unrecognized'}">
                    ${capture.recognized ? 'RECOGNIZED' : 'UNRECOGNIZED'}
                </span>
            </div>
        </div>
    `).join('');
}

function showOverlay(message, details, type = 'info') {
    overlay.style.display = 'flex';
    overlayMessage.textContent = message;
    overlayDetails.textContent = details;

    overlayIcon.innerHTML = '';
    if (type === 'success') {
        overlayIcon.innerHTML = '<svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>';
        overlay.className = 'recognition-overlay success-overlay';
    } else if (type === 'error') {
        overlayIcon.innerHTML = '<svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="3"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        overlay.className = 'recognition-overlay error-overlay';
    } else if (type === 'warning') {
        overlayIcon.innerHTML = '<svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#ca8a04" stroke-width="3"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
        overlay.className = 'recognition-overlay warning-overlay';
    } else {
        overlayIcon.innerHTML = '<svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#0891b2" stroke-width="3"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
        overlay.className = 'recognition-overlay';
    }
}

function hideOverlay() {
    overlay.style.display = 'none';
}

function monitorCameraConnection() {
    if (!stream) return;

    stream.getTracks().forEach(track => {
        track.onended = () => {
            console.warn('Camera track ended unexpectedly');
            attemptReconnect();
        };
    });
}

async function attemptReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        showToast('Camera disconnected. Please restart manually.', 'error');
        stopCamera();
        return;
    }

    reconnectAttempts++;
    showToast(`Attempting to reconnect camera (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`, 'warning');

    await new Promise(resolve => setTimeout(resolve, 2000));

    try {
        await startCamera();
        showToast('Camera reconnected successfully', 'success');
        reconnectAttempts = 0;
    } catch (error) {
        console.error('Reconnect failed:', error);
        await attemptReconnect();
    }
}

toggleBtn.addEventListener('click', () => {
    if (stream) {
        stopCamera();
    } else {
        startCamera();
    }
});

captureBtn.addEventListener('click', () => {
    performRecognition();
});

document.querySelectorAll('.time-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        currentAction = e.currentTarget.dataset.action;
    });
});

document.addEventListener('DOMContentLoaded', () => {
    getCameras();
});
