/**
 * Generator UI Module
 *
 * Handles generator tab UI functions: console output, progress, file loading.
 */

import { getCalculatorPyodide } from './pyodide-init.js';
import { exportAssemblyGLB } from './viewer-3d.js';

// Track hobbing progress for time estimation
let hobbingStartTime = null;
let hobbingTimeEstimate = null;
let hobbingRateHistory = [];  // Track rate observations for EMA
let lastHobbingPercent = 0;  // Track last percent for incremental calculation
let lastHobbingTime = null;  // Track last update time
const RATE_HISTORY_SIZE = 5;  // Keep last 5 observations (recent only)
const EMA_ALPHA = 0.3;  // Smoothing factor for EMA

// Track which part we're currently generating (for export step detection)
let currentGenerationPhase = 'worm';  // 'worm' or 'wheel'

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
 * Update design summary display using spec-table styling (matching design tab).
 * @param {object} design - Design object
 */
export function updateDesignSummary(design) {
    const summary = document.getElementById('gen-design-summary');
    const banner = document.getElementById('gen-design-banner');

    if (!design || !design.worm || !design.wheel) {
        summary.innerHTML = '<p>No design loaded. Use a Design tab or upload JSON.</p>';
        if (banner) banner.style.display = 'none';
        return;
    }

    const worm = design.worm;
    const wheel = design.wheel;
    const assembly = design.assembly || {};
    const manufacturing = design.manufacturing || {};
    const features = design.features || {};
    const wormType = worm.type || (worm.throat_curvature_radius_mm ? 'globoid' : 'cylindrical');
    const moduleStr = `m${Number(worm.module_mm).toFixed(1)}`;
    const ratioStr = `r${assembly.ratio}`;
    const profileStr = manufacturing.profile || 'ZA';
    const profileLabels = { 'ZA': 'ZA (straight)', 'ZK': 'ZK (convex)', 'ZI': 'ZI (involute)' };

    // Compact one-liner banner
    if (banner) {
        banner.textContent = `Design: ${moduleStr} ${ratioStr} ${wormType} ${profileStr}`;
        banner.style.display = 'block';
    }

    // Helpers
    const fmt = (v, d = 2) => v != null ? Number(v).toFixed(d) : '\u2014';
    const fmtMm = (v, d = 2) => v != null ? `${Number(v).toFixed(d)} mm` : '\u2014';
    const fmtDeg = (v, d = 1) => v != null ? `${Number(v).toFixed(d)}\u00b0` : '\u2014';

    function section(title, rows, open = false) {
        const openAttr = open ? ' open' : '';
        let html = `<details class="gen-spec-details"${openAttr}><summary class="gen-spec-toggle">${title}</summary><table class="spec-table">`;
        for (const [label, value] of rows) {
            if (value === undefined || value === null) continue;
            html += `<tr><td class="spec-label">${label}</td><td class="spec-value">${value}</td></tr>`;
        }
        html += '</table></details>';
        return html;
    }

    let html = '';

    // OVERVIEW (expanded by default)
    const overviewRows = [
        ['Module', fmtMm(worm.module_mm, 3)],
        ['Ratio', `${assembly.ratio}:1`],
        ['Centre Distance', fmtMm(assembly.centre_distance_mm)],
        ['Profile', profileLabels[profileStr] || profileStr],
    ];
    if (wormType === 'globoid') overviewRows.push(['Worm Type', 'Globoid']);
    html += section('Overview', overviewRows, true);

    // WORM
    const wormRows = [
        ['Tip Diameter', fmtMm(worm.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(worm.pitch_diameter_mm)],
        ['Root Diameter', fmtMm(worm.root_diameter_mm)],
        ['Lead Angle', fmtDeg(worm.lead_angle_deg)],
    ];
    if (manufacturing.worm_length_mm) {
        wormRows.push(['Length', fmtMm(manufacturing.worm_length_mm, 1)]);
    }
    html += section('Worm', wormRows);

    // WHEEL
    const wheelRows = [
        ['Tip Diameter', fmtMm(wheel.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(wheel.pitch_diameter_mm)],
        ['Teeth', wheel.num_teeth],
    ];
    if (manufacturing.wheel_width_mm) {
        wheelRows.push(['Face Width', fmtMm(manufacturing.wheel_width_mm, 1)]);
    }
    html += section('Wheel', wheelRows);

    // ASSEMBLY
    const asmRows = [
        ['Efficiency', assembly.efficiency_percent != null ? `~${Math.round(assembly.efficiency_percent)}%` : '\u2014'],
        ['Self-Locking', assembly.self_locking ? 'Yes' : 'No'],
        ['Pressure Angle', fmtDeg(assembly.pressure_angle_deg)],
    ];
    html += section('Assembly', asmRows);

    // SHAFT INTERFACE (if features present)
    const shaftRows = [];
    const wormF = features.worm || {};
    const wheelF = features.wheel || {};

    if (wormF.bore_type === 'custom' && wormF.bore_diameter_mm) {
        let s = `${fmt(wormF.bore_diameter_mm, 1)} mm`;
        if (wormF.anti_rotation === 'DIN6885') s += ' + keyway';
        else if (wormF.anti_rotation === 'ddcut') s += ' + DD-cut';
        shaftRows.push(['Worm Bore', s]);
    } else if (wormF.bore_type === 'none') {
        shaftRows.push(['Worm Bore', 'Solid']);
    }

    if (wheelF.bore_type === 'custom' && wheelF.bore_diameter_mm) {
        let s = `${fmt(wheelF.bore_diameter_mm, 1)} mm`;
        if (wheelF.anti_rotation === 'DIN6885') s += ' + keyway';
        else if (wheelF.anti_rotation === 'ddcut') s += ' + DD-cut';
        shaftRows.push(['Wheel Bore', s]);
    } else if (wheelF.bore_type === 'none') {
        shaftRows.push(['Wheel Bore', 'Solid']);
    }

    if (shaftRows.length > 0) {
        html += section('Shaft Interface', shaftRows);
    }

    summary.innerHTML = html;
}

/**
 * Update validation status badge in generator tab.
 * @param {boolean} valid - Whether the design is valid
 * @param {Array} messages - Validation messages array
 */
export function updateGeneratorValidation(valid, messages) {
    const badge = document.getElementById('gen-validation-status');
    if (!badge) return;

    if (!messages || messages.length === 0) {
        // No messages — hide badge
        badge.classList.remove('visible', 'status-valid', 'status-error', 'status-warning');
        return;
    }

    const errors = messages.filter(m => m.severity === 'error').length;
    const warnings = messages.filter(m => m.severity === 'warning').length;

    badge.classList.add('visible');
    badge.classList.remove('status-valid', 'status-error', 'status-warning');

    if (errors > 0) {
        badge.classList.add('status-error');
        badge.textContent = `${errors} error${errors > 1 ? 's' : ''}${warnings > 0 ? `, ${warnings} warning${warnings > 1 ? 's' : ''}` : ''}`;
    } else if (warnings > 0) {
        badge.classList.add('status-warning');
        badge.textContent = `${warnings} warning${warnings > 1 ? 's' : ''}`;
    } else {
        badge.classList.add('status-valid');
        badge.textContent = 'Design valid';
    }
}

/**
 * Hide validation badge in generator tab (e.g. when loading from file/paste).
 */
export function hideGeneratorValidation() {
    const badge = document.getElementById('gen-validation-status');
    if (badge) {
        badge.classList.remove('visible', 'status-valid', 'status-error', 'status-warning');
    }
}

/**
 * Show the downloads section (after successful generation).
 */
export function showDownloadsSection() {
    const section = document.getElementById('gen-downloads-section');
    if (section) section.classList.add('visible');
}

/**
 * Hide the downloads section.
 */
export function hideDownloadsSection() {
    const section = document.getElementById('gen-downloads-section');
    if (section) section.classList.remove('visible');
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
    const steps = ['parse', 'worm', 'worm-export', 'wheel', 'wheel-export', 'package'];
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
        // Hide sub-progress (but don't reset timing - let hideProgressIndicator do that)
        subProgress.style.display = 'none';
    } else {
        // Show and update sub-progress
        subProgress.style.display = 'block';

        // Track start time when actual work begins (percent > 0, not at 0%)
        if (hobbingStartTime === null && percent > 0) {
            hobbingStartTime = Date.now();
            lastHobbingTime = Date.now();
            lastHobbingPercent = percent;
            hobbingRateHistory = [];  // Reset history
            console.log('[Time Tracking] Started at', new Date(hobbingStartTime).toISOString(), 'percent=', percent);
        }

        // Calculate time estimate using INCREMENTAL rates (after 5% completion)
        if (percent >= 5 && hobbingStartTime !== null && lastHobbingTime !== null) {
            const now = Date.now();
            const incrementalElapsed = (now - lastHobbingTime) / 1000;  // seconds since LAST update
            const percentDelta = percent - lastHobbingPercent;  // percent progress since LAST update

            if (percentDelta > 0 && incrementalElapsed > 0) {
                // Calculate INCREMENTAL rate (recent steps only, not average from start)
                const incrementalRate = incrementalElapsed / percentDelta;

                // Add to history
                hobbingRateHistory.push({ percent, rate: incrementalRate });
                if (hobbingRateHistory.length > RATE_HISTORY_SIZE) {
                    hobbingRateHistory.shift();
                }

                // Calculate EMA of RECENT rates
                let emaRate = incrementalRate;
                if (hobbingRateHistory.length >= 2) {
                    let numerator = 0;
                    let denominator = 0;
                    for (let i = 0; i < hobbingRateHistory.length; i++) {
                        const weight = Math.pow(EMA_ALPHA, hobbingRateHistory.length - 1 - i);
                        numerator += hobbingRateHistory[i].rate * weight;
                        denominator += weight;
                    }
                    emaRate = numerator / denominator;
                }

                // Apply slowdown prediction based on known O(n²) complexity
                // Virtual hobbing gets progressively slower as geometry complexity increases
                let complexityMultiplier = 1.0;
                if (percent < 30) {
                    // Early phase: assume rate will triple by completion
                    complexityMultiplier = 3.0;
                } else if (percent < 60) {
                    // Middle phase: assume rate will double by completion
                    complexityMultiplier = 2.0;
                } else if (percent < 85) {
                    // Late phase: assume rate will increase 50% more
                    complexityMultiplier = 1.5;
                } else {
                    // Final phase: rate is mostly stable
                    complexityMultiplier = 1.2;
                }

                // Also detect empirical trend from recent observations
                let empiricalMultiplier = 1.0;
                if (hobbingRateHistory.length >= 4) {
                    const midpoint = Math.floor(hobbingRateHistory.length / 2);
                    const firstHalf = hobbingRateHistory.slice(0, midpoint);
                    const secondHalf = hobbingRateHistory.slice(midpoint);

                    const avgFirst = firstHalf.reduce((sum, obs) => sum + obs.rate, 0) / firstHalf.length;
                    const avgSecond = secondHalf.reduce((sum, obs) => sum + obs.rate, 0) / secondHalf.length;

                    if (avgSecond > avgFirst) {
                        const acceleration = avgSecond / avgFirst;
                        empiricalMultiplier = Math.min(2.0, acceleration);
                    }
                }

                // Use the higher of the two predictions (more conservative)
                const trendMultiplier = Math.max(complexityMultiplier, empiricalMultiplier);

                // Estimate remaining time
                const percentRemaining = 100 - percent;
                const baseEstimate = percentRemaining * emaRate;
                const adjustedEstimate = baseEstimate * trendMultiplier;
                hobbingTimeEstimate = Math.max(1, adjustedEstimate);

                console.log(`[Time Estimate] ${percent.toFixed(1)}% | Incr: ${incrementalRate.toFixed(1)}s/% | EMA: ${emaRate.toFixed(1)}s/% | Trend: ${trendMultiplier.toFixed(2)}x | Est: ${hobbingTimeEstimate.toFixed(1)}s remaining`);

                // Update last tracking values
                lastHobbingTime = now;
                lastHobbingPercent = percent;
            }
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
                const seconds = Math.max(1, Math.round(hobbingTimeEstimate % 60));

                if (minutes > 0) {
                    displayMessage += ` - Estimated: ${minutes}m ${seconds}s remaining`;
                } else if (seconds > 0) {
                    displayMessage += ` - Estimated: ${seconds}s remaining`;
                }
            }

            progressText.textContent = displayMessage;
        }
    }
}

/**
 * Reset hobbing time tracking
 */
export function resetHobbingTimer() {
    hobbingStartTime = null;
    hobbingTimeEstimate = null;
    hobbingRateHistory = [];  // Clear history
    lastHobbingPercent = 0;
    lastHobbingTime = null;
    currentGenerationPhase = 'worm';  // Reset phase
    console.log('[Time Tracking] Timer reset');
}

/**
 * Show cancel button and hide generate button
 */
export function showCancelButton() {
    document.getElementById('generate-btn').style.display = 'none';
    const cancelBtn = document.getElementById('cancel-generate-btn');
    if (cancelBtn) cancelBtn.style.display = 'block';
}

/**
 * Hide cancel button and show generate button
 */
export function hideCancelButton() {
    document.getElementById('generate-btn').style.display = '';
    const cancelBtn = document.getElementById('cancel-generate-btn');
    if (cancelBtn) cancelBtn.style.display = '';
}

/**
 * Handle progress updates from worker
 * @param {string} message - Progress message
 * @param {number} percent - Progress percentage
 */
export function handleProgress(message, percent) {
    // Detect which step we're on based on message content
    const msgLower = message.toLowerCase();
    console.log('[Progress]', message, 'percent:', percent);

    // Don't show progress indicator for initialization messages (Pyodide loading, package installation)
    const isInitMessage = msgLower.includes('loading pyodide') ||
                          msgLower.includes('installing') ||
                          msgLower.includes('loading micropip') ||
                          msgLower.includes('loading numpy') ||
                          msgLower.includes('generator ready') ||
                          msgLower.includes('package') && !msgLower.includes('generating');

    // Only show progress indicator for actual generation steps
    const isGenerationMessage = msgLower.includes('parsing') ||
                                msgLower.includes('generating') ||
                                msgLower.includes('exporting') ||
                                msgLower.includes('starting geometry') ||
                                msgLower.includes('% complete');

    const progressContainer = document.getElementById('generation-progress');
    if (progressContainer && isGenerationMessage && !isInitMessage) {
        progressContainer.style.display = 'block';
    }

    // Check for hobbing progress FIRST (before generic wheel messages)
    // Hobbing messages: "X% complete (Y/Z cuts)" or "Hobbing simulation"
    const isHobbingProgress = (msgLower.includes('% complete') && msgLower.includes('cuts')) ||
                              (msgLower.includes('hobbing') && percent !== null && percent !== undefined);

    if (isHobbingProgress) {
        console.log('[Hobbing Progress Detected]', message, 'percent:', percent);
        // Make sure we're in wheel step
        const wheelIndicator = document.querySelector('.step-indicator[data-step="wheel"]');
        if (!wheelIndicator || !wheelIndicator.classList.contains('active')) {
            setMainStep('wheel', 'Generating wheel gear...');
        }
        updateSubProgress(percent, message);
    }
    // Parsing/setup step
    else if (msgLower.includes('parsing') || msgLower.includes('parameters') || msgLower.includes('📋') || msgLower.includes('starting geometry')) {
        currentGenerationPhase = 'worm';  // Reset phase at start
        setMainStep('parse', 'Parsing parameters...');
        updateSubProgress(null);
    }
    // Worm generation step (🔩 emoji or "generating worm" but NOT "generating wheel")
    else if (msgLower.includes('🔩') || (msgLower.includes('generating worm') && !msgLower.includes('wheel'))) {
        currentGenerationPhase = 'worm';
        setMainStep('worm', 'Generating worm gear...');
        updateSubProgress(null);
    }
    // Wheel generation step (⚙️ emoji or "generating wheel")
    else if (msgLower.includes('⚙️') || msgLower.includes('generating wheel')) {
        currentGenerationPhase = 'wheel';
        setMainStep('wheel', 'Generating wheel gear...');
        updateSubProgress(null);
    }
    // Export step (STEP or STL or 3MF format) - check which phase we're in
    else if (msgLower.includes('exporting') && (msgLower.includes('step') || msgLower.includes('stl') || msgLower.includes('3mf'))) {
        if (currentGenerationPhase === 'worm') {
            setMainStep('worm-export', 'Exporting worm...');
        } else {
            setMainStep('wheel-export', 'Exporting wheel...');
        }
        updateSubProgress(null);
    }
    // Package step (creating ZIP)
    else if (msgLower.includes('creating zip') || msgLower.includes('package ready') || msgLower.includes('complete package')) {
        setMainStep('package', 'Creating package...');
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

    // Hide sub-progress and reset timing
    updateSubProgress(null);
    resetHobbingTimer();

    // Hide cancel button, show generate button
    hideCancelButton();
}

/**
 * Handle generation completion
 * @param {object} data - Completion data from worker
 */
export async function handleGenerateComplete(data) {
    console.log('[DEBUG] handleGenerateComplete received:', {
        hasWorm: !!data.worm,
        hasWheel: !!data.wheel,
        hasWorm3mf: !!data.worm_3mf,
        hasWheel3mf: !!data.wheel_3mf,
        hasWormStl: !!data.worm_stl,
        hasWheelStl: !!data.wheel_stl,
        hasAssembly3mf: !!data.assembly_3mf,
        success: data.success
    });

    const { worm, wheel, worm_3mf, wheel_3mf, worm_stl, wheel_stl, assembly_3mf, mesh_rotation_deg, success } = data;

    if (!success) {
        appendToConsole('⚠️ Generation completed with errors');
        hideProgressIndicator();
        return;
    }

    // Set final step
    setMainStep('package', 'Generation complete');
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
from wormgear.calculator import validate_design, to_markdown
from wormgear.io import WormGearDesign, WormParams, WheelParams, AssemblyParams
from wormgear.enums import Hand, WormProfile, WormType

# Parse design
design_data = json.loads(design_json_str)

# Create parameter objects from JSON (unified package uses _mm/_deg suffixes already)
worm_params = WormParams(**design_data['worm'])
wheel_params = WheelParams(**design_data['wheel'])
assembly_params = AssemblyParams(**design_data['assembly'])

# Create WormGearDesign
design = WormGearDesign(
    worm=worm_params,
    wheel=wheel_params,
    assembly=assembly_params
)

# Validate and generate markdown
validation = validate_design(design)
to_markdown(design)
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

    // Store data for ZIP creation and 3D preview
    window.generatedSTEP = {
        worm: worm,
        wheel: wheel,
        worm_3mf: worm_3mf,
        wheel_3mf: wheel_3mf,
        worm_stl: worm_stl,
        wheel_stl: wheel_stl,
        assembly_3mf: assembly_3mf,
        mesh_rotation_deg: mesh_rotation_deg || 0,
        markdown: markdown
    };

    // Enable download button and show downloads section
    const downloadBtn = document.getElementById('download-zip');
    if (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.onclick = createAndDownloadZip;
    }
    showDownloadsSection();

    // Enable 3D Preview tab if mesh data is available (prefer 3MF, fall back to STL)
    const previewBtn = document.getElementById('preview-tab-btn');
    if (previewBtn && ((worm_3mf && wheel_3mf) || (worm_stl && wheel_stl))) {
        previewBtn.disabled = false;
    }

    appendToConsole('Complete package ready for download');

    // Hide cancel button, show generate button for next generation
    hideCancelButton();
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
            hasWorm3mf: !!stepData.worm_3mf,
            hasWheel3mf: !!stepData.wheel_3mf,
            hasWormStl: !!stepData.worm_stl,
            hasWheelStl: !!stepData.wheel_stl,
            hasAssembly3mf: !!stepData.assembly_3mf,
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

        // Add 3MF files (preferred for 3D printing - explicit units and better precision)
        if (stepData.worm_3mf) {
            const worm3mfBinary = atob(stepData.worm_3mf);
            const worm3mfBytes = new Uint8Array(worm3mfBinary.length);
            for (let i = 0; i < worm3mfBinary.length; i++) {
                worm3mfBytes[i] = worm3mfBinary.charCodeAt(i);
            }
            zip.file('worm.3mf', worm3mfBytes);
            appendToConsole(`  ✓ Added worm.3mf (${(worm3mfBytes.length / 1024).toFixed(1)} KB)`);
        }

        if (stepData.wheel_3mf) {
            const wheel3mfBinary = atob(stepData.wheel_3mf);
            const wheel3mfBytes = new Uint8Array(wheel3mfBinary.length);
            for (let i = 0; i < wheel3mfBinary.length; i++) {
                wheel3mfBytes[i] = wheel3mfBinary.charCodeAt(i);
            }
            zip.file('wheel.3mf', wheel3mfBytes);
            appendToConsole(`  ✓ Added wheel.3mf (${(wheel3mfBytes.length / 1024).toFixed(1)} KB)`);
        }

        // Add assembly 3MF (pre-positioned by Python - correct geometry)
        if (stepData.assembly_3mf) {
            const asm3mfBinary = atob(stepData.assembly_3mf);
            const asm3mfBytes = new Uint8Array(asm3mfBinary.length);
            for (let i = 0; i < asm3mfBinary.length; i++) {
                asm3mfBytes[i] = asm3mfBinary.charCodeAt(i);
            }
            zip.file('assembly.3mf', asm3mfBytes);
            appendToConsole(`  ✓ Added assembly.3mf (${(asm3mfBytes.length / 1024).toFixed(1)} KB)`);
        }

        // Generate assembly GLB (both parts positioned at correct centre distance)
        const hasMesh = stepData.assembly_3mf || (stepData.worm_3mf && stepData.wheel_3mf) || (stepData.worm_stl && stepData.wheel_stl);
        if (hasMesh && design) {
            try {
                appendToConsole('  Generating assembly.glb...');
                const glbBuffer = await exportAssemblyGLB(
                    {
                        assembly_3mf: stepData.assembly_3mf,
                        worm_3mf: stepData.worm_3mf,
                        wheel_3mf: stepData.wheel_3mf,
                        worm_stl: stepData.worm_stl,
                        wheel_stl: stepData.wheel_stl,
                    },
                    {
                        centre_distance_mm: design.assembly.centre_distance_mm,
                        mesh_rotation_deg: stepData.mesh_rotation_deg || 0,
                    }
                );
                zip.file('assembly.glb', glbBuffer);
                appendToConsole(`  ✓ Added assembly.glb (${(glbBuffer.byteLength / 1024).toFixed(1)} KB)`);
            } catch (err) {
                console.error('GLB export failed:', err);
                appendToConsole(`  ⚠️ assembly.glb failed: ${err.message}`);
            }
        }

        // Add STL files (for compatibility)
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
