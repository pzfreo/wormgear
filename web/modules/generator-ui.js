/**
 * Generator UI Module
 *
 * Handles generator tab UI functions: console output, progress, file loading.
 */

import { getCalculatorPyodide } from './pyodide-init.js';

// Track hobbing progress for time estimation
let hobbingStartTime = null;
let hobbingTimeEstimate = null;

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
 * Set main progress step
 * @param {string} step - Step name: 'parse', 'worm', 'wheel', 'export', 'complete'
 * @param {string} message - Step description
 */
function setMainStep(step, message) {
    // Update main step text
    const mainStepText = document.getElementById('main-step-text');
    if (mainStepText) {
        mainStepText.textContent = message;
    }

    // Update step indicators
    const steps = ['parse', 'worm', 'wheel', 'export'];
    steps.forEach(s => {
        const indicator = document.querySelector(`.step-indicator[data-step="${s}"]`);
        if (!indicator) return;

        if (s === step) {
            // Current step
            indicator.classList.remove('complete');
            indicator.classList.add('active');
        } else if (steps.indexOf(s) < steps.indexOf(step)) {
            // Completed step
            indicator.classList.remove('active');
            indicator.classList.add('complete');
        } else {
            // Future step
            indicator.classList.remove('active', 'complete');
        }
    });
}

/**
 * Show/hide and update sub-progress (hobbing)
 * @param {number} percent - Progress percentage (0-100)
 * @param {string} message - Optional message
 */
function updateSubProgress(percent, message = null) {
    const subProgress = document.getElementById('sub-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('sub-progress-text');

    if (!subProgress) return;

    if (percent === null || percent < 0) {
        // Hide sub-progress and reset timing
        subProgress.style.display = 'none';
        hobbingStartTime = null;
        hobbingTimeEstimate = null;
    } else {
        // Show and update sub-progress
        subProgress.style.display = 'block';

        // Track start time on first progress update
        if (hobbingStartTime === null && percent > 0) {
            hobbingStartTime = Date.now();
        }

        // Calculate time estimate after 5% completion
        if (percent >= 5 && hobbingStartTime !== null) {
            const elapsed = (Date.now() - hobbingStartTime) / 1000; // seconds
            const estimatedTotal = (elapsed / percent) * 100;
            const remaining = estimatedTotal - elapsed;
            hobbingTimeEstimate = remaining;
        }

        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${Math.round(percent)}%`;
        }

        if (progressText) {
            let displayMessage = message || 'Virtual hobbing in progress...';

            // Add time estimate if available
            if (hobbingTimeEstimate !== null && percent < 100) {
                const minutes = Math.floor(hobbingTimeEstimate / 60);
                const seconds = Math.round(hobbingTimeEstimate % 60);

                if (minutes > 0) {
                    displayMessage += ` - Estimated: ${minutes}m ${seconds}s remaining`;
                } else {
                    displayMessage += ` - Estimated: ${seconds}s remaining`;
                }
            }

            progressText.textContent = displayMessage;
        }
    }
}

/**
 * Handle progress updates from worker
 * @param {string} message - Progress message
 * @param {number} percent - Progress percentage
 */
export function handleProgress(message, percent) {
    const progressContainer = document.getElementById('generation-progress');
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }

    // Detect which step we're on based on message content
    const msgLower = message.toLowerCase();
    console.log('[Progress]', message, 'percent:', percent);

    if (msgLower.includes('parsing') || msgLower.includes('parameters') || msgLower.includes('📋')) {
        setMainStep('parse', 'Parsing parameters...');
        updateSubProgress(null);
    } else if (msgLower.includes('🔩') || (msgLower.includes('worm') && !msgLower.includes('wheel'))) {
        setMainStep('worm', 'Generating worm gear...');
        updateSubProgress(null);
    } else if (msgLower.includes('⚙️') || msgLower.includes('wheel') || msgLower.includes('hobbing')) {
        setMainStep('wheel', 'Generating wheel gear...');
        // Show sub-progress for hobbing
        if (msgLower.includes('hobbing') || msgLower.includes('step')) {
            updateSubProgress(percent, message);
        } else {
            updateSubProgress(null);
        }
    } else if (msgLower.includes('export') || msgLower.includes('step format') || msgLower.includes('stl format')) {
        setMainStep('export', 'Exporting files...');
        updateSubProgress(null);
    }

    appendToConsole(message);
}

/**
 * Hide progress indicator
 */
export function hideProgressIndicator() {
    const progressContainer = document.getElementById('generation-progress');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }

    // Reset step indicators
    document.querySelectorAll('.step-indicator').forEach(indicator => {
        indicator.classList.remove('active', 'complete');
    });

    // Hide sub-progress
    updateSubProgress(null);
}

/**
 * Handle generation completion
 * @param {object} data - Completion data from worker
 */
export async function handleGenerateComplete(data) {
    console.log('[DEBUG] handleGenerateComplete received:', {
        hasWorm: !!data.worm,
        hasWheel: !!data.wheel,
        hasWormStl: !!data.worm_stl,
        hasWheelStl: !!data.wheel_stl,
        success: data.success
    });

    const { worm, wheel, worm_stl, wheel_stl, success } = data;

    if (!success) {
        appendToConsole('⚠️ Generation completed with errors');
        hideProgressIndicator();
        return;
    }

    // Set final step
    setMainStep('export', 'Generation complete');
    updateSubProgress(null);

    // Mark all steps as complete
    document.querySelectorAll('.step-indicator').forEach(indicator => {
        indicator.classList.remove('active');
        indicator.classList.add('complete');
    });

    appendToConsole('✓ Generation complete');

    // Generate markdown using calculator Pyodide (which has wormcalc module loaded)
    appendToConsole('Generating documentation...');
    let markdown = '';

    try {
        // Get calculator Pyodide instance
        const calculatorPyodide = getCalculatorPyodide();

        if (calculatorPyodide && window.currentGeneratedDesign) {
            // Set design data in Python
            calculatorPyodide.globals.set('design_json_str', JSON.stringify(window.currentGeneratedDesign));

            // Generate markdown
            const result = calculatorPyodide.runPython(`
import json
from wormcalc import to_markdown, validate_design
from wormcalc.core import WormGearDesign, WormParameters, WheelParameters, AssemblyParameters, ManufacturingParameters

# Parse design
design_data = json.loads(design_json_str)
design = WormGearDesign(
    worm=WormParameters(**design_data['worm']),
    wheel=WheelParameters(**design_data['wheel']),
    assembly=AssemblyParameters(**design_data['assembly']),
    manufacturing=ManufacturingParameters(**design_data['manufacturing']) if 'manufacturing' in design_data else None
)

# Validate and generate markdown (return the result)
validation = validate_design(design)
to_markdown(design, validation)
            `);

            // Convert Pyodide result to string
            markdown = String(result);
            console.log('[DEBUG] Generated markdown length:', markdown.length);
            appendToConsole(`✓ Documentation generated (${markdown.length} bytes)`);
        } else {
            appendToConsole('⚠️ Calculator not loaded - markdown will be empty');
        }
    } catch (error) {
        console.error('Error generating markdown:', error);
        appendToConsole(`⚠️ Could not generate markdown: ${error.message}`);
    }

    // Store data for ZIP creation
    window.generatedSTEP = {
        worm: worm,
        wheel: wheel,
        worm_stl: worm_stl,
        wheel_stl: wheel_stl,
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

        console.log('[DEBUG] Creating ZIP with:', {
            hasDesign: !!design,
            hasWorm: !!stepData.worm,
            hasWheel: !!stepData.wheel,
            hasWormStl: !!stepData.worm_stl,
            hasWheelStl: !!stepData.wheel_stl,
            hasMarkdown: !!stepData.markdown,
            markdownLength: stepData.markdown ? stepData.markdown.length : 0
        });

        // Create ZIP
        const zip = new JSZip();

        // Add JSON file
        zip.file('design.json', JSON.stringify(design, null, 2));

        // Add markdown file
        if (stepData.markdown && stepData.markdown.length > 0) {
            zip.file('design.md', stepData.markdown);
            appendToConsole(`  ✓ Added design.md (${stepData.markdown.length} bytes)`);
        } else {
            appendToConsole('  ⚠️ No markdown documentation available');
        }

        // Add STEP files (decode from base64)
        if (stepData.worm) {
            const wormBinary = atob(stepData.worm);
            const wormBytes = new Uint8Array(wormBinary.length);
            for (let i = 0; i < wormBinary.length; i++) {
                wormBytes[i] = wormBinary.charCodeAt(i);
            }
            zip.file('worm.step', wormBytes);
            appendToConsole(`  ✓ Added worm.step (${(wormBytes.length / 1024).toFixed(1)} KB)`);
        }

        if (stepData.wheel) {
            const wheelBinary = atob(stepData.wheel);
            const wheelBytes = new Uint8Array(wheelBinary.length);
            for (let i = 0; i < wheelBinary.length; i++) {
                wheelBytes[i] = wheelBinary.charCodeAt(i);
            }
            zip.file('wheel.step', wheelBytes);
            appendToConsole(`  ✓ Added wheel.step (${(wheelBytes.length / 1024).toFixed(1)} KB)`);
        }

        // Add STL files (decode from base64)
        if (stepData.worm_stl) {
            const wormStlBinary = atob(stepData.worm_stl);
            const wormStlBytes = new Uint8Array(wormStlBinary.length);
            for (let i = 0; i < wormStlBinary.length; i++) {
                wormStlBytes[i] = wormStlBinary.charCodeAt(i);
            }
            zip.file('worm.stl', wormStlBytes);
            appendToConsole(`  ✓ Added worm.stl (${(wormStlBytes.length / 1024).toFixed(1)} KB)`);
        }

        if (stepData.wheel_stl) {
            const wheelStlBinary = atob(stepData.wheel_stl);
            const wheelStlBytes = new Uint8Array(wheelStlBinary.length);
            for (let i = 0; i < wheelStlBinary.length; i++) {
                wheelStlBytes[i] = wheelStlBinary.charCodeAt(i);
            }
            zip.file('wheel.stl', wheelStlBytes);
            appendToConsole(`  ✓ Added wheel.stl (${(wheelStlBytes.length / 1024).toFixed(1)} KB)`);
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
