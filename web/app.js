// Wormgear Complete Design System - Browser Application
// Clean modular architecture with validated JS<->Python bridge

import { calculateBoreSize, getCalculatedBores, updateBoreDisplaysAndDefaults, updateAntiRotationOptions, setupBoreEventListeners } from './modules/bore-calculator.js';
import { updateValidationUI } from './modules/validation-ui.js';
import { getInputs } from './modules/parameter-handler.js';
import { parseCalculatorResponse } from './modules/schema-validator.js';
import { getCalculatorPyodide, getGeneratorWorker, initCalculator, initGenerator } from './modules/pyodide-init.js';
import { appendToConsole, updateDesignSummary, handleProgress, hideProgressIndicator, handleGenerateComplete } from './modules/generator-ui.js';

// Global state
let currentDesign = null;
let currentValidation = null;
let currentMarkdown = null;
let generatorTabVisited = false;
let currentGenerationId = 0;  // Track generation to ignore cancelled results
let isGenerating = false;  // Track if generation is in progress

// ============================================================================
// UTILITIES
// ============================================================================

/**
 * Debounce function to limit how often a function can fire.
 * @param {Function} func - The function to debounce
 * @param {number} wait - Milliseconds to wait before calling
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ============================================================================
// UI HELPERS
// ============================================================================

/**
 * Get the active worm type from the design tab's data attribute.
 * @returns {string} 'cylindrical' or 'globoid'
 */
function getActiveWormType() {
    return document.getElementById('design-tab')?.dataset.wormType || 'cylindrical';
}

/**
 * Show/hide the throating note in the generator tab.
 * Shown when virtual hobbing is selected but design has throated_wheel: false.
 */
function updateThroatingNote() {
    const note = document.getElementById('gen-throating-note');
    if (!note) return;
    const isVirtualHobbing = document.getElementById('gen-wheel-generation')?.value === 'virtual-hobbing';
    const isThroated = currentDesign?.manufacturing?.throated_wheel;
    note.style.display = (isVirtualHobbing && !isThroated) ? 'block' : 'none';
}

/**
 * Sync generator UI controls from a loaded design's manufacturing settings.
 * Called when loading JSON from calculator, file upload, or "Open in Generator".
 */
function syncGeneratorUI(design) {
    if (!design) return;
    const mfg = design.manufacturing || {};

    // Worm generation method
    const genWormEl = document.getElementById('gen-worm-generation');
    if (genWormEl && mfg.generation_method) {
        genWormEl.value = mfg.generation_method;
    }
}

/**
 * Map a validation message code to a spec sheet section name.
 * Returns the section title where the message should appear inline.
 */
function getMessageSection(code) {
    if (!code) return 'General';

    // Overview section
    if (code.startsWith('MODULE_') || code.startsWith('PROFILE_') || code.startsWith('PRESSURE_ANGLE'))
        return 'Overview';

    // Worm section
    if (code.startsWith('LEAD_ANGLE') || code.startsWith('WORM_IMPOSSIBLE') ||
        code.startsWith('WORM_ZERO') || code.startsWith('WORM_ROOT_EXCEEDS') ||
        code.startsWith('WORM_TOO_THIN') || code.startsWith('WORM_TOO_THICK') ||
        code.startsWith('WORM_LENGTH') || code.startsWith('WORM_TYPE') ||
        code.startsWith('THROAT_REDUCTION'))
        return 'Worm';

    // Wheel section
    if (code.startsWith('WHEEL_IMPOSSIBLE') || code.startsWith('WHEEL_ZERO') ||
        code.startsWith('WHEEL_ROOT_EXCEEDS') || code.startsWith('WHEEL_TIP_REDUCTION') ||
        code.startsWith('TEETH_'))
        return 'Wheel';

    // Assembly section
    if (code.startsWith('EFFICIENCY') || code.startsWith('CLEARANCE') ||
        code.startsWith('GEOMETRIC_') || code.startsWith('CENTRE_DISTANCE'))
        return 'Assembly';

    // Shaft Interface section
    if (code.includes('BORE') || code.includes('DDCUT'))
        return 'Shaft Interface';

    return 'General';
}

/**
 * Render inline validation messages for a given section.
 * @param {Array} messages - All validation messages
 * @param {string} sectionName - Section to filter for
 * @returns {string} HTML string of inline messages
 */
function renderInlineMessages(messages, sectionName) {
    const sectionMsgs = messages.filter(m => getMessageSection(m.code) === sectionName);
    if (sectionMsgs.length === 0) return '';

    let html = '<div class="spec-messages">';
    for (const msg of sectionMsgs) {
        html += `<div class="spec-msg spec-msg-${msg.severity}">`;
        html += `<span class="spec-msg-text">${msg.message}</span>`;
        if (msg.suggestion) {
            html += `<span class="spec-msg-suggestion">${msg.suggestion}</span>`;
        }
        html += '</div>';
    }
    html += '</div>';
    return html;
}

/**
 * Render a structured specification sheet from the design JSON.
 * Replaces the old plain-text <pre> output with formatted HTML tables.
 * Validation messages are rendered inline within each section.
 *
 * @param {object} design - The full design JSON object
 * @param {object} output - The calculator output (for recommended bore info)
 * @param {Array} [messages] - Validation messages to render inline
 */
function renderSpecSheet(design, output, messages = []) {
    const container = document.getElementById('spec-sheet');
    if (!container || !design) {
        container.innerHTML = '<p class="spec-sheet-placeholder">Enter parameters to calculate design</p>';
        return;
    }

    const worm = design.worm || {};
    const wheel = design.wheel || {};
    const asm = design.assembly || {};
    const mfg = design.manufacturing || {};
    const features = design.features || {};

    const wormType = worm.type || 'cylindrical';
    const profileLabels = { 'ZA': 'ZA (straight flanks)', 'ZK': 'ZK (convex flanks)', 'ZI': 'ZI (involute)' };
    const profileLabel = profileLabels[mfg.profile] || mfg.profile || 'ZA';

    // Helper: format number to fixed decimals, or dash if missing
    const fmt = (val, decimals = 2) => val != null ? Number(val).toFixed(decimals) : '\u2014';
    const fmtMm = (val, decimals = 2) => val != null ? `${Number(val).toFixed(decimals)} mm` : '\u2014';
    const fmtDeg = (val, decimals = 1) => val != null ? `${Number(val).toFixed(decimals)}\u00b0` : '\u2014';

    // Helper: build a table section with inline validation messages
    function section(title, rows) {
        let html = `<div class="spec-section"><h3 class="spec-section-title">${title}</h3><table class="spec-table">`;
        for (const [label, value] of rows) {
            if (value === undefined || value === null) continue;
            html += `<tr><td class="spec-label">${label}</td><td class="spec-value">${value}</td></tr>`;
        }
        html += '</table>';
        html += renderInlineMessages(messages, title);
        html += '</div>';
        return html;
    }

    let html = '';

    // OVERVIEW
    html += section('Overview', [
        ['Ratio', `${asm.ratio}:1`],
        ['Module', fmtMm(worm.module_mm, 3)],
        ['Centre Distance', fmtMm(asm.centre_distance_mm)],
        ['Hand', (asm.hand || 'right').charAt(0).toUpperCase() + (asm.hand || 'right').slice(1).toLowerCase()],
        ['Profile', profileLabel],
        wormType === 'globoid' ? ['Worm Type', 'Globoid'] : null,
    ].filter(Boolean));

    // WORM
    const wormRows = [
        ['Tip Diameter', fmtMm(worm.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(worm.pitch_diameter_mm)],
        ['Root Diameter', fmtMm(worm.root_diameter_mm)],
        ['Lead', fmtMm(worm.lead_mm, 3)],
        ['Lead Angle', fmtDeg(worm.lead_angle_deg)],
        ['Starts', worm.num_starts],
    ];
    if (mfg.worm_length_mm) {
        wormRows.push(['Length', `${fmt(mfg.worm_length_mm, 1)} mm <span class="spec-note">(recommended)</span>`]);
    }
    if (wormType === 'globoid' && worm.throat_curvature_radius_mm) {
        wormRows.push(['Throat Pitch Radius', fmtMm(worm.throat_curvature_radius_mm)]);
    }
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        wormRows.push(['Throat Reduction', fmtMm(worm.throat_reduction_mm)]);
    }
    html += section('Worm', wormRows);

    // WHEEL
    const wheelRows = [
        ['Tip Diameter', fmtMm(wheel.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(wheel.pitch_diameter_mm)],
        ['Root Diameter', fmtMm(wheel.root_diameter_mm)],
        ['Teeth', wheel.num_teeth],
    ];
    if (mfg.wheel_width_mm) {
        wheelRows.push(['Face Width', `${fmt(mfg.wheel_width_mm, 1)} mm <span class="spec-note">(recommended)</span>`]);
    }
    if (wheel.helix_angle_deg) {
        wheelRows.push(['Helix Angle', fmtDeg(wheel.helix_angle_deg)]);
    }
    wheelRows.push(['Throated', mfg.throated_wheel ? 'Yes' : 'No']);

    // Show min OD at throat for globoid
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        const arcR = worm.tip_diameter_mm / 2 - worm.throat_reduction_mm;
        const margin = worm.addendum_mm + 0.5 * wheel.addendum_mm;
        const minBlankR = asm.centre_distance_mm - arcR + margin;
        const throatOD = 2 * Math.min(wheel.tip_diameter_mm / 2, minBlankR);
        wheelRows.push(['Min OD at Throat', fmtMm(throatOD)]);
    }
    html += section('Wheel', wheelRows);

    // ASSEMBLY
    html += section('Assembly', [
        ['Pressure Angle', fmtDeg(asm.pressure_angle_deg)],
        ['Backlash', fmtMm(asm.backlash_mm, 3)],
        ['Efficiency', asm.efficiency_percent != null ? `~${Math.round(asm.efficiency_percent)}%` : '\u2014'],
        ['Self-Locking', asm.self_locking ? 'Yes' : 'No'],
    ]);

    // SHAFT INTERFACE
    const shaftRows = [];
    const wormFeatures = features.worm || {};
    const wheelFeatures = features.wheel || {};

    if (wormFeatures.bore_type === 'custom' && wormFeatures.bore_diameter_mm) {
        let wormBoreStr = `${fmt(wormFeatures.bore_diameter_mm, 1)} mm`;
        if (wormFeatures.anti_rotation === 'DIN6885') {
            wormBoreStr += ' + DIN 6885 keyway';
        } else if (wormFeatures.anti_rotation === 'ddcut') {
            wormBoreStr += ' + DD-cut';
        }
        shaftRows.push(['Worm Bore', wormBoreStr]);
    } else if (wormFeatures.bore_type === 'none') {
        shaftRows.push(['Worm Bore', 'Solid (no bore)']);
    }

    if (wheelFeatures.bore_type === 'custom' && wheelFeatures.bore_diameter_mm) {
        let wheelBoreStr = `${fmt(wheelFeatures.bore_diameter_mm, 1)} mm`;
        if (wheelFeatures.anti_rotation === 'DIN6885') {
            wheelBoreStr += ' + DIN 6885 keyway';
        } else if (wheelFeatures.anti_rotation === 'ddcut') {
            wheelBoreStr += ' + DD-cut';
        }
        shaftRows.push(['Wheel Bore', wheelBoreStr]);
    } else if (wheelFeatures.bore_type === 'none') {
        shaftRows.push(['Wheel Bore', 'Solid (no bore)']);
    }

    if (shaftRows.length > 0) {
        html += section('Shaft Interface', shaftRows);
    }

    // Render any "General" messages that don't map to a specific section
    const generalHtml = renderInlineMessages(messages, 'General');
    if (generalHtml) {
        html += `<div class="spec-section">${generalHtml}</div>`;
    }

    container.innerHTML = html;
}

// Update throat reduction auto hint based on geometry
function updateThroatReductionAutoHint() {
    const hint = document.getElementById('throat-reduction-auto-value');
    if (!hint) return;

    if (currentDesign?.worm && currentDesign?.wheel && currentDesign?.assembly) {
        const wormPitchRadius = currentDesign.worm.pitch_diameter_mm / 2;
        const wheelPitchRadius = currentDesign.wheel.pitch_diameter_mm / 2;
        const centerDistance = currentDesign.assembly.centre_distance_mm;

        // Geometrically correct throat reduction
        let throatReduction = wormPitchRadius - (centerDistance - wheelPitchRadius);
        if (throatReduction <= 0) {
            throatReduction = currentDesign.worm.pitch_diameter_mm * 0.02; // fallback
        }

        hint.textContent = `\u2248 ${throatReduction.toFixed(2)}mm (geometric: worm_r - (CD - wheel_r))`;
    } else {
        hint.textContent = `Calculated from worm/wheel geometry`;
    }
}

// ============================================================================
// TAB SWITCHING
// ============================================================================

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const designTab = document.getElementById('design-tab');
    const generatorTab = document.getElementById('generator-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Update active tab button
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            if (targetTab === 'cylindrical' || targetTab === 'globoid') {
                // Both design tabs show the same #design-tab content
                designTab.classList.add('active');
                generatorTab.classList.remove('active');

                // Set worm type on the design tab container
                designTab.dataset.wormType = targetTab;

                // Lazy load calculator if needed
                if (!getCalculatorPyodide()) {
                    initCalculatorTab();
                } else {
                    // Recalculate with new worm type
                    calculate();
                }
            } else if (targetTab === 'generator') {
                // Show generator tab
                designTab.classList.remove('active');
                generatorTab.classList.add('active');

                // Hide progress indicator on tab switch
                const progressContainer = document.getElementById('generation-progress');
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }

                // Generator should already be loading in background
                if (!getGeneratorWorker()) {
                    initGeneratorTab(false);
                }

                // Auto-load from calculator on first visit
                if (!generatorTabVisited) {
                    generatorTabVisited = true;
                    if (currentDesign) {
                        loadFromCalculator();
                    }
                }
            }
        });
    });
}

// ============================================================================
// CALCULATOR TAB
// ============================================================================

async function initCalculatorTab() {
    await initCalculator(() => {
        loadFromUrl();
        calculate();

        // Start loading generator in background after calculator is ready (no modal)
        if (!getGeneratorWorker()) {
            initGeneratorTab(false).catch(err => {
                console.log('Generator background loading failed (non-fatal):', err);
            });
        }
    });
}

async function calculate() {
    const calculatorPyodide = getCalculatorPyodide();
    if (!calculatorPyodide) return;

    try {
        const mode = document.getElementById('mode').value;
        const wormType = getActiveWormType();

        // Get validated inputs (throws if invalid)
        const inputs = getInputs(mode, wormType);

        // Serialize to JSON for Python
        const inputJson = JSON.stringify(inputs);

        // Set input for Python bridge
        calculatorPyodide.globals.set('input_json', inputJson);

        // Call the clean Python bridge
        const result = calculatorPyodide.runPython(`
from wormgear.calculator.js_bridge import calculate
calculate(input_json)
        `);

        // Parse and validate the response
        const { output, design } = parseCalculatorResponse(result);

        if (!output.success) {
            throw new Error(output.error);
        }

        // Update global state
        currentDesign = design;
        currentValidation = output.valid;
        currentMarkdown = output.markdown;

        // Update UI - pass Python's bore recommendations
        updateBoreDisplaysAndDefaults(currentDesign, output.recommended_worm_bore, output.recommended_wheel_bore);
        updateThroatReductionAutoHint();
        renderSpecSheet(currentDesign, output, output.messages || []);
        updateValidationUI(output.valid, output.messages || []);

        // Enable all export buttons after successful calculation
        // Validation errors are shown prominently but don't block exports —
        // the user may know better than the validator
        document.getElementById('copy-json').disabled = false;
        document.getElementById('download-json').disabled = false;
        document.getElementById('download-pdf').disabled = false;
        document.getElementById('download-design-package').disabled = false;
        document.getElementById('copy-link').disabled = false;
        document.getElementById('open-in-generator').disabled = false;

        // Keep generator JSON in sync if user has visited that tab
        if (generatorTabVisited) {
            document.getElementById('json-input').value = JSON.stringify(currentDesign, null, 2);
        }

    } catch (error) {
        console.error('Calculation error:', error);
        document.getElementById('spec-sheet').innerHTML = `<p class="spec-sheet-placeholder" style="color: var(--color-error);">Error: ${error.message}</p>`;
    }
}

function loadFromUrl() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('mode')) {
        const mode = params.get('mode');
        document.getElementById('mode').value = mode;

        // Trigger mode change to show correct input group
        document.querySelectorAll('.input-group').forEach(group => {
            group.style.display = group.dataset.mode === mode ? 'block' : 'none';
        });

        // Handle worm_type from URL - switch to correct tab
        if (params.has('worm_type')) {
            const wormType = params.get('worm_type');
            if (wormType === 'globoid') {
                // Activate the globoid tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelector('.tab[data-tab="globoid"]').classList.add('active');
                document.getElementById('design-tab').dataset.wormType = 'globoid';
            }
        }

        // Set inputs based on mode
        params.forEach((value, key) => {
            if (key === 'mode' || key === 'worm_type') return;

            // Handle checkbox states
            if (key === 'use_standard_module') {
                document.getElementById('use-standard-module').checked = value === 'true';
                return;
            }
            if (key === 'od_as_maximum') {
                document.getElementById('od-as-maximum').checked = value === 'true';
                return;
            }

            // Convert underscore to hyphen for other parameters
            const normalizedKey = key.replace(/_/g, '-');

            // Try to find the input element
            const el = document.getElementById(normalizedKey) || document.getElementById(`${normalizedKey}-${getModeSuffix(mode)}`);
            if (el) {
                if (el.type === 'checkbox') {
                    el.checked = value === 'true';
                } else {
                    el.value = value;
                }
            }
        });

        // Recalculate with URL parameters
        calculate();
    }
}

// Get mode suffix for input IDs
function getModeSuffix(mode) {
    const suffixes = {
        'from-wheel': 'fw',
        'from-module': 'fm',
        'from-centre-distance': 'fcd'
    };
    return suffixes[mode] || '';
}

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

function getDesignFilename() {
    if (!currentDesign) return 'wormgear-design';
    const m = currentDesign.worm?.module_mm;
    const r = currentDesign.assembly?.ratio;
    const type = currentDesign.worm?.type === 'globoid' ? 'globoid' : 'cyl';
    const parts = ['wormgear'];
    if (m != null) parts.push(`m${m}`);
    if (r != null) parts.push(`r${r}`);
    parts.push(type);
    return parts.join('-');
}

function copyJSON() {
    if (!currentDesign) return;
    navigator.clipboard.writeText(JSON.stringify(currentDesign, null, 2));
    showNotification('JSON copied to clipboard!');
}

function downloadJSON() {
    if (!currentDesign) return;
    const blob = new Blob([JSON.stringify(currentDesign, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = getDesignFilename() + '.json';
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Build a jsPDF document from the current design data.
 * @returns {object|null} jsPDF document instance, or null if unavailable
 */
function buildPDFDocument() {
    if (!currentDesign || !window.jspdf) return null;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });

    const design = currentDesign;
    const worm = design.worm || {};
    const wheel = design.wheel || {};
    const asm = design.assembly || {};
    const mfg = design.manufacturing || {};
    const features = design.features || {};
    const wormType = worm.type || 'cylindrical';

    const pageW = doc.internal.pageSize.getWidth();
    const margin = 15;
    const contentW = pageW - 2 * margin;
    let y = margin;

    // Colours
    const black = [30, 41, 59];
    const muted = [100, 116, 139];
    const sectionBg = [241, 245, 249];
    const borderCol = [226, 232, 240];

    // Helpers
    const fmt = (val, d = 2) => val != null ? Number(val).toFixed(d) : '\u2014';

    function drawTitle(text) {
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(16);
        doc.setTextColor(...black);
        doc.text(text, margin, y);
        y += 5;
        doc.setDrawColor(...black);
        doc.setLineWidth(0.5);
        doc.line(margin, y, margin + contentW, y);
        y += 6;
    }

    function drawSectionHeader(text) {
        doc.setFillColor(...sectionBg);
        doc.setDrawColor(...borderCol);
        doc.rect(margin, y, contentW, 5.5, 'FD');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(7);
        doc.setTextColor(...muted);
        doc.text(text.toUpperCase(), margin + 2, y + 3.8);
        y += 5.5;
    }

    function drawRow(label, value, isLast = false) {
        const rowH = 5.5;
        doc.setDrawColor(...borderCol);
        // Left and right borders
        doc.line(margin, y, margin, y + rowH);
        doc.line(margin + contentW, y, margin + contentW, y + rowH);
        // Bottom border
        if (isLast) {
            doc.line(margin, y + rowH, margin + contentW, y + rowH);
        } else {
            doc.setDrawColor(235, 235, 235);
            doc.line(margin, y + rowH, margin + contentW, y + rowH);
        }

        // Label
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8.5);
        doc.setTextColor(...muted);
        doc.text(label, margin + 2, y + 3.8);

        // Value — strip any HTML tags (like <span class="spec-note">)
        const cleanValue = String(value).replace(/<[^>]*>/g, '').trim();
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8.5);
        doc.setTextColor(...black);
        doc.text(cleanValue, margin + contentW - 2, y + 3.8, { align: 'right' });

        y += rowH;
    }

    function drawSection(title, rows) {
        // Check if section fits on page (header + rows)
        const sectionH = 5.5 + rows.length * 5.5 + 4;
        if (y + sectionH > 280) {
            doc.addPage();
            y = margin;
        }
        drawSectionHeader(title);
        rows.forEach((row, i) => drawRow(row[0], row[1], i === rows.length - 1));
        y += 4;
    }

    // --- Build the PDF ---

    // Header
    doc.setFont('courier', 'bold');
    doc.setFontSize(18);
    doc.setTextColor(...black);
    doc.text('WORMGEAR.STUDIO', margin, y);
    y += 8;
    drawTitle('Specification Sheet');

    // Profile labels
    const profileLabels = { 'ZA': 'ZA (straight flanks)', 'ZK': 'ZK (convex flanks)', 'ZI': 'ZI (involute)' };

    // OVERVIEW
    const overviewRows = [
        ['Ratio', `${asm.ratio}:1`],
        ['Module', `${fmt(worm.module_mm, 3)} mm`],
        ['Centre Distance', `${fmt(asm.centre_distance_mm)} mm`],
        ['Hand', (asm.hand || 'right').charAt(0).toUpperCase() + (asm.hand || 'right').slice(1).toLowerCase()],
        ['Profile', profileLabels[mfg.profile] || mfg.profile || 'ZA'],
    ];
    if (wormType === 'globoid') overviewRows.push(['Worm Type', 'Globoid']);
    drawSection('Overview', overviewRows);

    // WORM
    const wormRows = [
        ['Tip Diameter', `${fmt(worm.tip_diameter_mm)} mm`],
        ['Pitch Diameter', `${fmt(worm.pitch_diameter_mm)} mm`],
        ['Root Diameter', `${fmt(worm.root_diameter_mm)} mm`],
        ['Lead', `${fmt(worm.lead_mm, 3)} mm`],
        ['Lead Angle', `${fmt(worm.lead_angle_deg, 1)}\u00b0`],
        ['Starts', `${worm.num_starts}`],
    ];
    if (mfg.worm_length_mm) wormRows.push(['Length', `${fmt(mfg.worm_length_mm, 1)} mm (recommended)`]);
    if (wormType === 'globoid' && worm.throat_curvature_radius_mm) {
        wormRows.push(['Throat Pitch Radius', `${fmt(worm.throat_curvature_radius_mm)} mm`]);
    }
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        wormRows.push(['Throat Reduction', `${fmt(worm.throat_reduction_mm)} mm`]);
    }
    drawSection('Worm', wormRows);

    // WHEEL
    const wheelRows = [
        ['Tip Diameter', `${fmt(wheel.tip_diameter_mm)} mm`],
        ['Pitch Diameter', `${fmt(wheel.pitch_diameter_mm)} mm`],
        ['Root Diameter', `${fmt(wheel.root_diameter_mm)} mm`],
        ['Teeth', `${wheel.num_teeth}`],
    ];
    if (mfg.wheel_width_mm) wheelRows.push(['Face Width', `${fmt(mfg.wheel_width_mm, 1)} mm (recommended)`]);
    if (wheel.helix_angle_deg) wheelRows.push(['Helix Angle', `${fmt(wheel.helix_angle_deg, 1)}\u00b0`]);
    wheelRows.push(['Throated', mfg.throated_wheel ? 'Yes' : 'No']);
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        const arcR = worm.tip_diameter_mm / 2 - worm.throat_reduction_mm;
        const mg = worm.addendum_mm + 0.5 * wheel.addendum_mm;
        const minBlankR = asm.centre_distance_mm - arcR + mg;
        const throatOD = 2 * Math.min(wheel.tip_diameter_mm / 2, minBlankR);
        wheelRows.push(['Min OD at Throat', `${fmt(throatOD)} mm`]);
    }
    drawSection('Wheel', wheelRows);

    // ASSEMBLY
    drawSection('Assembly', [
        ['Pressure Angle', `${fmt(asm.pressure_angle_deg, 1)}\u00b0`],
        ['Backlash', `${fmt(asm.backlash_mm, 3)} mm`],
        ['Efficiency', asm.efficiency_percent != null ? `~${Math.round(asm.efficiency_percent)}%` : '\u2014'],
        ['Self-Locking', asm.self_locking ? 'Yes' : 'No'],
    ]);

    // SHAFT INTERFACE
    const shaftRows = [];
    const wormF = features.worm || {};
    const wheelF = features.wheel || {};
    if (wormF.bore_type === 'custom' && wormF.bore_diameter_mm) {
        let s = `${fmt(wormF.bore_diameter_mm, 1)} mm`;
        if (wormF.anti_rotation === 'DIN6885') s += ' + DIN 6885 keyway';
        else if (wormF.anti_rotation === 'ddcut') s += ' + DD-cut';
        shaftRows.push(['Worm Bore', s]);
    } else if (wormF.bore_type === 'none') {
        shaftRows.push(['Worm Bore', 'Solid (no bore)']);
    }
    if (wheelF.bore_type === 'custom' && wheelF.bore_diameter_mm) {
        let s = `${fmt(wheelF.bore_diameter_mm, 1)} mm`;
        if (wheelF.anti_rotation === 'DIN6885') s += ' + DIN 6885 keyway';
        else if (wheelF.anti_rotation === 'ddcut') s += ' + DD-cut';
        shaftRows.push(['Wheel Bore', s]);
    } else if (wheelF.bore_type === 'none') {
        shaftRows.push(['Wheel Bore', 'Solid (no bore)']);
    }
    if (shaftRows.length > 0) drawSection('Shaft Interface', shaftRows);

    // Footer
    y += 4;
    doc.setDrawColor(...borderCol);
    doc.line(margin, y, margin + contentW, y);
    y += 4;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(...muted);
    doc.text(`Generated by WORMGEAR.STUDIO \u2014 ${new Date().toLocaleDateString()}`, margin, y);

    return doc;
}

/**
 * Generate PDF bytes for embedding in a ZIP.
 * @returns {ArrayBuffer|null}
 */
function generatePDFBytes() {
    const doc = buildPDFDocument();
    return doc ? doc.output('arraybuffer') : null;
}

/**
 * Generate and download a PDF specification sheet.
 */
function downloadPDF() {
    if (!currentDesign) {
        alert('No design calculated yet');
        return;
    }
    if (!window.jspdf) {
        alert('jsPDF library not loaded');
        return;
    }
    const doc = buildPDFDocument();
    if (doc) doc.save(getDesignFilename() + '.pdf');
}

/**
 * Download a design package (ZIP with JSON, Markdown, and PDF spec sheet).
 */
async function downloadDesignPackage() {
    if (!currentDesign) {
        alert('No design calculated yet');
        return;
    }

    if (!window.JSZip) {
        alert('JSZip library not loaded');
        return;
    }

    const zip = new JSZip();
    const filename = getDesignFilename();

    // Add JSON
    zip.file('design.json', JSON.stringify(currentDesign, null, 2));

    // Add Markdown
    if (currentMarkdown) {
        zip.file('design.md', currentMarkdown);
    }

    // Add PDF spec sheet (generated via jsPDF)
    if (window.jspdf) {
        const pdfBytes = generatePDFBytes();
        if (pdfBytes) {
            zip.file('spec-sheet.pdf', pdfBytes);
        }
    }

    // Generate and download
    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.zip`;
    a.click();
    URL.revokeObjectURL(url);

    showNotification('Design package downloaded');
}

function copyLink() {
    const mode = document.getElementById('mode').value;
    const wormType = getActiveWormType();
    const inputs = getInputs(mode, wormType);
    const params = new URLSearchParams();

    params.set('mode', mode);
    params.set('worm_type', wormType);

    // Add calculator inputs
    Object.entries(inputs.calculator || {}).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
            params.set(key, value);
        }
    });

    // Add checkbox states
    params.set('use_standard_module', document.getElementById('use-standard-module').checked);
    if (mode === 'envelope') {
        params.set('od_as_maximum', document.getElementById('od-as-maximum').checked);
    }

    const url = `${window.location.origin}${window.location.pathname}?${params}`;

    navigator.clipboard.writeText(url)
        .then(() => {
            showNotification('Share link copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy link', true);
        });
}

/**
 * Switch to generator tab with the current design pre-loaded.
 */
function openInGenerator() {
    if (!currentDesign) {
        alert('No design calculated yet.');
        return;
    }

    // Load design into generator
    document.getElementById('json-input').value = JSON.stringify(currentDesign, null, 2);
    updateDesignSummary(currentDesign);
    syncGeneratorUI(currentDesign);
    updateThroatingNote();

    // Switch to generator tab
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(t => t.classList.remove('active'));
    document.querySelector('.tab[data-tab="generator"]').classList.add('active');

    document.getElementById('design-tab').classList.remove('active');
    document.getElementById('generator-tab').classList.add('active');

    // Mark as visited so auto-load doesn't overwrite
    generatorTabVisited = true;

    // Hide progress indicator
    const progressContainer = document.getElementById('generation-progress');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }

    // Start generator if not already running
    if (!getGeneratorWorker()) {
        initGeneratorTab(false);
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    appendToConsole('Loaded design from calculator');
}

// Show temporary notification
function showNotification(message, isError = false) {
    const notification = document.createElement('div');
    notification.className = isError ? 'notification notification-error' : 'notification notification-success';
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('notification-show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('notification-show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 2000);
}

// ============================================================================
// GENERATOR TAB
// ============================================================================

async function initGeneratorTab(showModal = true) {
    await initGenerator(showModal, setupWorkerMessageHandler);
}

function setupWorkerMessageHandler(worker) {
    worker.onmessage = (e) => {
        const { type, message, percent, error, stack } = e.data;

        switch (type) {
            case 'INIT_COMPLETE':
                console.log('[Generator] Initialization complete');
                const statusEl = document.getElementById('generator-loading-status');
                if (statusEl) {
                    statusEl.textContent = 'Generator ready';
                    statusEl.style.color = '#22c55e';
                }
                const btn = document.getElementById('generate-btn');
                if (btn) btn.disabled = false;
                break;
            case 'INIT_ERROR':
                console.error('[Generator] Initialization failed:', error);
                const statusElError = document.getElementById('generator-loading-status');
                if (statusElError) {
                    statusElError.textContent = `Error: ${error}`;
                    statusElError.style.color = '#dc3545';
                }
                break;
            case 'LOG':
                if (isGenerating) {
                    handleProgress(message, null);
                } else {
                    // During init, show worker progress in the status element
                    const initStatus = document.getElementById('generator-loading-status');
                    if (initStatus && initStatus.textContent !== 'Generator ready') {
                        initStatus.textContent = message;
                    }
                }
                break;
            case 'PROGRESS':
                if (isGenerating) {
                    handleProgress(message, percent);
                }
                break;
            case 'GENERATE_COMPLETE':
                if (isGenerating) {
                    isGenerating = false;
                    handleGenerateComplete(e.data);
                } else {
                    console.log('[Generator] Ignoring completion from cancelled generation');
                }
                break;
            case 'GENERATE_ERROR':
                if (isGenerating) {
                    isGenerating = false;
                    appendToConsole(`\u2717 Generation error: ${error}`);
                    if (stack) console.error('Worker error stack:', stack);
                    hideProgressIndicator();
                } else {
                    console.log('[Generator] Ignoring error from cancelled generation');
                }
                break;
        }
    };

    worker.onerror = (error) => {
        console.error('Worker error:', error);
        appendToConsole(`\u2717 Worker error: ${error.message}`);
    };
}

function loadFromCalculator() {
    if (!currentDesign) {
        alert('No design in calculator. Calculate a design first.');
        return;
    }

    document.getElementById('json-input').value = JSON.stringify(currentDesign, null, 2);
    updateDesignSummary(currentDesign);
    syncGeneratorUI(currentDesign);
    updateThroatingNote();
    appendToConsole('Loaded design from calculator');
}

function loadJSONFile() {
    document.getElementById('json-file-input').click();
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('json-input').value = e.target.result;
        try {
            const design = JSON.parse(e.target.result);
            updateDesignSummary(design);
            syncGeneratorUI(design);
            appendToConsole(`Loaded ${file.name}`);
        } catch (error) {
            appendToConsole(`Error parsing ${file.name}: ${error.message}`);
        }
    };
    reader.readAsText(file);
}

/**
 * Cancel ongoing generation
 */
async function cancelGeneration() {
    if (!isGenerating) {
        return;
    }

    currentGenerationId++;
    isGenerating = false;

    appendToConsole('Generation cancelled by user');
    appendToConsole('(Background process may continue - results will be ignored)');

    hideProgressIndicator();
}

async function generateGeometry(type) {
    const generatorWorker = getGeneratorWorker();
    if (!generatorWorker) {
        alert('Generator not loaded. Click "Load Generator" first.');
        return;
    }

    const jsonInput = document.getElementById('json-input').value;
    if (!jsonInput.trim()) {
        alert('No JSON input. Load from calculator or paste JSON.');
        return;
    }

    try {
        const designData = JSON.parse(jsonInput);

        if (!designData.worm || !designData.wheel || !designData.assembly) {
            appendToConsole('Invalid JSON structure');
            appendToConsole('Expected format: { "worm": {...}, "wheel": {...}, "assembly": {...} }');
            return;
        }

        // Read generation parameters from GENERATOR TAB UI (not from design JSON)
        const genWormGeneration = document.getElementById('gen-worm-generation');
        const genWheelGeneration = document.getElementById('gen-wheel-generation');
        const genHobbingPrecision = document.getElementById('gen-hobbing-precision');

        const generationMethod = genWormGeneration ? genWormGeneration.value : 'sweep';
        const virtualHobbing = genWheelGeneration ? genWheelGeneration.value === 'virtual-hobbing' : false;

        const hobbingPrecisionMap = { 'preview': 36, 'balanced': 72, 'high': 144 };
        const hobbingSteps = genHobbingPrecision ? (hobbingPrecisionMap[genHobbingPrecision.value] || 72) : 72;

        // Get profile from design JSON (it's a design concern, stays in calculator output)
        const manufacturing = designData.manufacturing || {};
        const profile = manufacturing.profile || 'ZA';

        // Auto-reduce hobbing steps for globoid worms
        const isGloboid = designData.worm?.type === 'globoid' ||
                          (designData.worm?.throat_curvature_radius_mm && designData.worm?.throat_curvature_radius_mm > 0);
        const GLOBOID_HOB_MAX_STEPS = 36;

        let effectiveHobbingSteps = hobbingSteps;
        if (virtualHobbing && isGloboid && hobbingSteps > GLOBOID_HOB_MAX_STEPS) {
            appendToConsole(`Auto-reducing hobbing steps from ${hobbingSteps} to ${GLOBOID_HOB_MAX_STEPS} for globoid worm`);
            effectiveHobbingSteps = GLOBOID_HOB_MAX_STEPS;
        }

        // Use canonical field names from schema v2.0
        let wormLength = manufacturing.worm_length_mm || 40;
        let wheelWidth = manufacturing.wheel_width_mm || null;

        // Start new generation
        currentGenerationId++;
        isGenerating = true;

        appendToConsole('Starting geometry generation...');
        appendToConsole(`Parameters: ${type}, Worm: ${generationMethod}, Virtual Hobbing: ${virtualHobbing}, Profile: ${profile}`);

        // Show and reset progress indicator
        const progressContainer = document.getElementById('generation-progress');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }

        // Reset step indicators
        document.querySelectorAll('.step-indicator').forEach(indicator => {
            indicator.classList.remove('active', 'complete');
        });

        // Reset timing and show cancel button
        const { showCancelButton, resetHobbingTimer } = await import('./modules/generator-ui.js');
        resetHobbingTimer();
        showCancelButton();

        // Store design data globally for download
        window.currentGeneratedDesign = designData;

        // Send generation request to worker
        generatorWorker.postMessage({
            type: 'GENERATE',
            data: {
                designData,
                generateType: type,
                generationMethod,
                virtualHobbing,
                hobbingSteps: effectiveHobbingSteps,
                profile,
                wormLength,
                wheelWidth
            }
        });

    } catch (error) {
        appendToConsole(`Error: ${error.message}`);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Check SharedArrayBuffer support (needed for generator WASM threading)
    if (!crossOriginIsolated) {
        console.warn('[Init] crossOriginIsolated is false — generator WASM may fail. Check COOP/COEP headers.');
    }

    initTabs();
    setupBoreEventListeners();

    // Learn mode toggle
    document.getElementById('learn-mode-toggle').addEventListener('change', (e) => {
        document.getElementById('app').classList.toggle('learn-mode', e.target.checked);
    });

    // Setup event listeners for calculator exports
    document.getElementById('copy-json').addEventListener('click', copyJSON);
    document.getElementById('download-json').addEventListener('click', downloadJSON);
    document.getElementById('download-pdf').addEventListener('click', downloadPDF);
    document.getElementById('download-design-package').addEventListener('click', downloadDesignPackage);
    document.getElementById('copy-link').addEventListener('click', copyLink);
    document.getElementById('open-in-generator').addEventListener('click', openInGenerator);

    // Setup event listeners for generator
    document.getElementById('load-from-calculator').addEventListener('click', loadFromCalculator);
    document.getElementById('load-json-file').addEventListener('click', loadJSONFile);
    document.getElementById('json-file-input').addEventListener('change', handleFileUpload);
    document.getElementById('generate-btn').addEventListener('click', () => generateGeometry('both'));
    document.getElementById('cancel-generate-btn').addEventListener('click', cancelGeneration);

    // Generator tab: wheel generation method switching (show/hide hobbing precision + throating note)
    document.getElementById('gen-wheel-generation').addEventListener('change', (e) => {
        const isVirtualHobbing = e.target.value === 'virtual-hobbing';
        document.getElementById('gen-hobbing-precision-group').style.display = isVirtualHobbing ? 'block' : 'none';
        updateThroatingNote();
    });

    // Update design summary when JSON is pasted or edited
    const jsonInput = document.getElementById('json-input');
    jsonInput.addEventListener('input', debounce(() => {
        try {
            const design = JSON.parse(jsonInput.value);
            if (design.worm && design.wheel && design.assembly) {
                updateDesignSummary(design);
                window.currentGeneratedDesign = design;
            }
        } catch (e) {
            // Invalid JSON - don't update summary
        }
    }, 500));

    // Mode switching
    document.getElementById('mode').addEventListener('change', (e) => {
        document.querySelectorAll('.input-group').forEach(group => {
            group.style.display = group.dataset.mode === e.target.value ? 'block' : 'none';
        });
    });

    // Throat reduction mode switching (auto vs custom)
    document.getElementById('throat-reduction-mode')?.addEventListener('change', (e) => {
        const isCustom = e.target.value === 'custom';
        document.getElementById('throat-reduction-custom').style.display = isCustom ? 'block' : 'none';
        document.getElementById('throat-reduction-auto-hint').style.display = isCustom ? 'none' : 'block';
        if (isCustom && currentDesign?.worm && currentDesign?.wheel && currentDesign?.assembly) {
            // Pre-fill with geometrically correct value
            const wormPitchRadius = currentDesign.worm.pitch_diameter_mm / 2;
            const wheelPitchRadius = currentDesign.wheel.pitch_diameter_mm / 2;
            const centerDistance = currentDesign.assembly.centre_distance_mm;

            let throatReduction = wormPitchRadius - (centerDistance - wheelPitchRadius);
            if (throatReduction <= 0) {
                throatReduction = currentDesign.worm.pitch_diameter_mm * 0.02; // fallback
            }
            document.getElementById('throat-reduction').value = throatReduction.toFixed(2);
        }
    });

    // Use recommended dimensions toggle
    document.getElementById('use-recommended-dims').addEventListener('change', (e) => {
        const customDims = document.getElementById('custom-dims-group');
        if (customDims) {
            customDims.style.display = e.target.checked ? 'none' : 'block';
        }

        // Populate with recommended values when toggling to custom
        if (!e.target.checked && currentDesign && currentDesign.manufacturing) {
            document.getElementById('worm-length').value = currentDesign.manufacturing.worm_length_mm || 40;
            document.getElementById('wheel-width').value = currentDesign.manufacturing.wheel_width_mm || 10;
        }
    });

    // Relief groove toggle
    document.getElementById('relief-groove').addEventListener('change', (e) => {
        const group = document.getElementById('relief-groove-group');
        if (group) {
            group.style.display = e.target.checked ? 'block' : 'none';
        }
    });

    // Relief groove type toggle (DIN 76 vs full-radius options)
    document.getElementById('groove-type').addEventListener('change', (e) => {
        const din76 = document.getElementById('din76-options');
        const fullRadius = document.getElementById('full-radius-options');
        if (din76) din76.style.display = e.target.value === 'din76' ? 'block' : 'none';
        if (fullRadius) fullRadius.style.display = e.target.value === 'full-radius' ? 'block' : 'none';
    });

    // Wheel max OD toggle
    document.getElementById('limit-wheel-od').addEventListener('change', (e) => {
        const group = document.getElementById('wheel-max-od-group');
        if (group) {
            group.style.display = e.target.checked ? 'block' : 'none';
        }
    });

    // Auto-recalculate on input changes — scoped to #design-tab only
    // (generator controls should NOT trigger calculate())
    const designTab = document.getElementById('design-tab');
    const designInputs = designTab.querySelectorAll('input, select');
    designInputs.forEach(input => {
        input.addEventListener('change', () => {
            if (getCalculatorPyodide()) calculate();
        });
    });

    // Trigger initial UI state updates
    const wormBoreType = document.getElementById('worm-bore-type');
    const wheelBoreType = document.getElementById('wheel-bore-type');

    if (wormBoreType) wormBoreType.dispatchEvent(new Event('change'));
    if (wheelBoreType) wheelBoreType.dispatchEvent(new Event('change'));

    // Calculator tab is active by default, so initialize it
    initCalculatorTab();
});

// Expose functions globally for HTML onclick handlers
window.calculate = calculate;
window.copyJSON = copyJSON;
window.downloadJSON = downloadJSON;
window.downloadPDF = downloadPDF;
window.downloadDesignPackage = downloadDesignPackage;
window.copyLink = copyLink;
window.loadFromCalculator = loadFromCalculator;
window.loadJSONFile = loadJSONFile;
window.generateGeometry = generateGeometry;
window.initGeneratorTab = initGeneratorTab;
window.openInGenerator = openInGenerator;
