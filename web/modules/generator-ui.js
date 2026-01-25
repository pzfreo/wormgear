/**
 * Generator UI Module
 *
 * Handles generator tab UI functions: console output, progress, file loading.
 */

/**
 * Append message to console output
 * @param {string} message - Message to append
 */
export function appendToConsole(message) {
    const consoleEl = document.getElementById('console-output');
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

/**
 * Update design summary display
 * @param {object} design - Design object
 */
export function updateDesignSummary(design) {
    const summary = document.getElementById('gen-design-summary');
    if (!design || !design.worm || !design.wheel) {
        summary.innerHTML = '<p>No design loaded. Use Calculator tab or upload JSON.</p>';
        return;
    }

    const manufacturing = design.manufacturing || {};
    summary.innerHTML = `
        <table style="width: 100%; font-size: 0.9em;">
            <tr><td><strong>Module:</strong></td><td>${design.worm.module_mm} mm</td></tr>
            <tr><td><strong>Ratio:</strong></td><td>${design.assembly.ratio}:1</td></tr>
            <tr><td><strong>Profile:</strong></td><td>${manufacturing.profile || 'ZA'} (${manufacturing.profile === 'ZK' ? '3D printing' : 'CNC machining'})</td></tr>
            <tr><td><strong>Worm Type:</strong></td><td>${design.worm.throat_curvature_radius_mm ? 'Globoid (hourglass)' : 'Cylindrical'}</td></tr>
            <tr><td><strong>Wheel Type:</strong></td><td>${manufacturing.throated_wheel ? 'Throated (hobbed)' : 'Helical'}</td></tr>
            <tr><td><strong>Hand:</strong></td><td>${design.assembly.hand}</td></tr>
        </table>
        <p style="margin-top: 0.5rem; font-size: 0.85em; color: #666;">
            These settings from your design will be used for generation.
        </p>
    `;
}

/**
 * Handle progress updates from worker
 * @param {string} message - Progress message
 * @param {number} percent - Progress percentage
 */
export function handleProgress(message, percent) {
    const progressContainer = document.getElementById('generation-progress');
    const progressText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');

    if (progressContainer) {
        progressContainer.style.display = 'block';
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${Math.round(percent)}%`;
        }
        if (progressText) {
            progressText.textContent = message;
        }
    }

    appendToConsole(message);
}

/**
 * Hide progress indicator
 */
export function hideProgressIndicator() {
    const progressBar = document.getElementById('generation-progress');
    if (progressBar) {
        progressBar.style.display = 'none';
    }
}

/**
 * Handle generation completion
 * @param {object} data - Completion data from worker
 */
export function handleGenerateComplete(data) {
    console.log('[DEBUG] handleGenerateComplete received:', {
        hasWorm: !!data.worm,
        hasWheel: !!data.wheel,
        success: data.success,
        wormLength: data.worm ? data.worm.length : 0,
        wheelLength: data.wheel ? data.wheel.length : 0
    });

    const { worm, wheel, success } = data;

    appendToConsole('✓ Generation complete');
    hideProgressIndicator();

    if (!success) {
        appendToConsole('⚠️ Generation completed with errors');
        return;
    }

    // Convert base64 STEP data to blob URLs
    let wormUrl = null;
    let wheelUrl = null;

    try {
        if (worm) {
            console.log('[DEBUG] Decoding worm base64...');
            const wormBinary = atob(worm);
            const wormBytes = new Uint8Array(wormBinary.length);
            for (let i = 0; i < wormBinary.length; i++) {
                wormBytes[i] = wormBinary.charCodeAt(i);
            }
            const wormBlob = new Blob([wormBytes], { type: 'application/octet-stream' });
            wormUrl = URL.createObjectURL(wormBlob);
            console.log('[DEBUG] Worm blob URL created:', wormUrl);
        }

        if (wheel) {
            console.log('[DEBUG] Decoding wheel base64...');
            const wheelBinary = atob(wheel);
            const wheelBytes = new Uint8Array(wheelBinary.length);
            for (let i = 0; i < wheelBinary.length; i++) {
                wheelBytes[i] = wheelBinary.charCodeAt(i);
            }
            const wheelBlob = new Blob([wheelBytes], { type: 'application/octet-stream' });
            wheelUrl = URL.createObjectURL(wheelBlob);
            console.log('[DEBUG] Wheel blob URL created:', wheelUrl);
        }
    } catch (error) {
        console.error('[DEBUG] Error creating blob URLs:', error);
        appendToConsole(`Error preparing downloads: ${error.message}`);
        return;
    }

    // Enable download buttons
    const wormBtn = document.getElementById('download-worm');
    const wheelBtn = document.getElementById('download-wheel');

    console.log('[DEBUG] Download buttons:', {
        wormBtn: !!wormBtn,
        wheelBtn: !!wheelBtn,
        wormUrl: !!wormUrl,
        wheelUrl: !!wheelUrl
    });

    if (wormBtn && wormUrl) {
        wormBtn.disabled = false;
        wormBtn.onclick = () => {
            console.log('[DEBUG] Worm download clicked');
            downloadFile(wormUrl, 'worm.step');
        };
        console.log('[DEBUG] Worm button enabled');
    }

    if (wheelBtn && wheelUrl) {
        wheelBtn.disabled = false;
        wheelBtn.onclick = () => {
            console.log('[DEBUG] Wheel download clicked');
            downloadFile(wheelUrl, 'wheel.step');
        };
        console.log('[DEBUG] Wheel button enabled');
    }

    appendToConsole('STEP files ready for download');
}

/**
 * Download file from blob URL
 * @param {string} url - Blob URL
 * @param {string} filename - Filename for download
 */
function downloadFile(url, filename) {
    console.log('[DEBUG] downloadFile called:', { url, filename });
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    console.log('[DEBUG] Download triggered');
}
