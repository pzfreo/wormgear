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
        hasMarkdown: !!data.markdown,
        success: data.success
    });

    const { worm, wheel, markdown, success } = data;

    appendToConsole('✓ Generation complete');
    hideProgressIndicator();

    if (!success) {
        appendToConsole('⚠️ Generation completed with errors');
        return;
    }

    // Store data for ZIP creation
    window.generatedSTEP = {
        worm: worm,
        wheel: wheel,
        markdown: markdown
    };

    // Enable download button
    const downloadBtn = document.getElementById('download-zip');
    if (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.onclick = createAndDownloadZip;
    }

    appendToConsole('Complete package ready for download');
}

/**
 * Create descriptive filename from design parameters
 * @param {object} design - Design data
 * @returns {string} Descriptive filename
 */
function createFilename(design) {
    try {
        const module = design.worm.module_mm || 1;
        const ratio = design.assembly.ratio || 30;
        const starts = design.worm.num_starts || 1;
        const teeth = design.wheel.num_teeth || 30;
        const wormType = design.manufacturing?.worm_type || 'cylindrical';

        // Format: wormgear_m2.0_30-1_cylindrical
        const moduleStr = module.toFixed(1).replace('.', '_');
        const typeStr = wormType === 'cylindrical' ? 'cyl' : 'glob';

        return `wormgear_m${moduleStr}_${teeth}-${starts}_${typeStr}`;
    } catch (error) {
        console.error('Error creating filename:', error);
        return 'wormgear_design';
    }
}

/**
 * Create and download ZIP file with all outputs
 */
async function createAndDownloadZip() {
    try {
        appendToConsole('Creating ZIP package...');

        if (!window.JSZip) {
            throw new Error('JSZip library not loaded');
        }

        const design = window.currentGeneratedDesign;
        const stepData = window.generatedSTEP;

        if (!design || !stepData) {
            throw new Error('No generated data available');
        }

        // Create ZIP
        const zip = new JSZip();

        // Add JSON file
        zip.file('design.json', JSON.stringify(design, null, 2));

        // Add markdown file
        if (stepData.markdown) {
            zip.file('design.md', stepData.markdown);
        }

        // Add STEP files (decode from base64)
        if (stepData.worm) {
            const wormBinary = atob(stepData.worm);
            const wormBytes = new Uint8Array(wormBinary.length);
            for (let i = 0; i < wormBinary.length; i++) {
                wormBytes[i] = wormBinary.charCodeAt(i);
            }
            zip.file('worm.step', wormBytes);
        }

        if (stepData.wheel) {
            const wheelBinary = atob(stepData.wheel);
            const wheelBytes = new Uint8Array(wheelBinary.length);
            for (let i = 0; i < wheelBinary.length; i++) {
                wheelBytes[i] = wheelBinary.charCodeAt(i);
            }
            zip.file('wheel.step', wheelBytes);
        }

        // Generate ZIP blob
        appendToConsole('Compressing files...');
        const blob = await zip.generateAsync({ type: 'blob' });

        // Create descriptive filename
        const filename = createFilename(design);

        // Trigger download
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.zip`;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        appendToConsole(`✓ Downloaded ${filename}.zip`);

    } catch (error) {
        console.error('Error creating ZIP:', error);
        appendToConsole(`✗ Error creating ZIP: ${error.message}`);
    }
}
