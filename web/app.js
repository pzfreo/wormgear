// Wormgear Complete Design System - Browser Application
// Clean modular architecture with validated JS<->Python bridge

import { calculateBoreSize, getCalculatedBores, updateBoreDisplaysAndDefaults, updateAntiRotationOptions, setupBoreEventListeners, setLoadingState } from './modules/bore-calculator.js';
import { updateValidationUI } from './modules/validation-ui.js';
import { getInputs } from './modules/parameter-handler.js';
import { parseCalculatorResponse } from './modules/schema-validator.js';
import { getCalculatorPyodide, getGeneratorWorker, initCalculator, initGenerator } from './modules/pyodide-init.js';
import { appendToConsole, updateDesignSummary, handleProgress, hideProgressIndicator, handleGenerateComplete, updateGeneratorValidation, hideGeneratorValidation } from './modules/generator-ui.js';
import { initViewer, loadMeshes, resizeViewer, pauseAnimation, resumeAnimation, isLoaded, togglePlayPause, setSpeed } from './modules/viewer-3d.js';
import { fmt, fmtMm, fmtDeg, PROFILE_LABELS, buildSpecRows, createDesignFilename } from './modules/format-utils.js';

// Global state
let currentDesign = null;
let currentValidation = null;
let currentMessages = null;
let currentMarkdown = null;
let currentOutput = null;  // Last calculator output (for recommended dims)
let generatorTabVisited = false;
let currentGenerationId = 0;  // Track generation to ignore cancelled results
let isGenerating = false;  // Track if generation is in progress
let isLoadingDesign = false;  // Suppress auto-recalculate during JSON round-trip loading

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
 * Get the active worm type from the worm-type dropdown.
 * @returns {string} 'cylindrical' or 'globoid'
 */
function getActiveWormType() {
    return document.getElementById('worm-type')?.value || 'cylindrical';
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
 * Enable/disable the sweep option for worm generation based on worm type.
 * Globoid worms only support loft — sweep is silently ignored by GloboidWormGeometry.
 * @param {string} wormType - 'cylindrical' or 'globoid'
 */
function updateGenerationMethodForWormType(wormType) {
    const genWormEl = document.getElementById('gen-worm-generation');
    if (!genWormEl) return;

    const sweepOption = genWormEl.querySelector('option[value="sweep"]');
    if (!sweepOption) return;

    if (wormType === 'globoid') {
        sweepOption.disabled = true;
        if (genWormEl.value === 'sweep') {
            genWormEl.value = 'loft';
        }
    } else {
        sweepOption.disabled = false;
    }
}

/**
 * Sync generator UI controls from a loaded design's manufacturing settings.
 * Called when loading JSON from calculator, file upload, or "Open in Generator".
 */
function syncGeneratorUI(design) {
    if (!design) return;
    const mfg = design.manufacturing || {};

    // Enforce globoid constraints before setting method
    const wormType = design.worm?.type || 'cylindrical';
    updateGenerationMethodForWormType(wormType);

    // Worm generation method
    const genWormEl = document.getElementById('gen-worm-generation');
    if (genWormEl && mfg.generation_method) {
        genWormEl.value = mfg.generation_method;
    }
}

/**
 * Load a design JSON into the design tab's input fields and recalculate.
 * Creates a true round-trip: JSON → design inputs → calculator → updated state.
 * Called when uploading a JSON file or pasting JSON in the generator tab.
 */
function loadDesignIntoDesignTab(design) {
    if (!design || !design.worm || !design.wheel || !design.assembly) return;

    // Suppress auto-recalculate and bore auto-fill during loading
    isLoadingDesign = true;
    setLoadingState(true);

    try {
        const worm = design.worm;
        const wheel = design.wheel;
        const asm = design.assembly;
        const mfg = design.manufacturing || {};
        const features = design.features || {};

        // --- 1. Worm type: set dropdown and data attribute ---
        const wormType = worm.type || 'cylindrical';
        const designTab = document.getElementById('design-tab');
        designTab.dataset.wormType = wormType;
        document.getElementById('worm-type').value = wormType;

        // --- 2. Mode: always use from-module (module + ratio are in every JSON) ---
        const modeEl = document.getElementById('mode');
        modeEl.value = 'from-module';
        document.querySelectorAll('.input-group').forEach(group => {
            group.style.display = group.dataset.mode === 'from-module' ? 'block' : 'none';
        });

        // --- 3. Core inputs ---
        document.getElementById('module').value = worm.module_mm;
        document.getElementById('ratio-fm').value = asm.ratio;
        document.getElementById('num-starts').value = worm.num_starts;
        document.getElementById('pressure-angle').value = asm.pressure_angle_deg;
        document.getElementById('hand').value = (asm.hand || 'right').toUpperCase();
        document.getElementById('backlash').value = asm.backlash_mm;
        // Profile shift: the user input maps to wheel profile shift (worm is always 0)
        document.getElementById('profile-shift').value = wheel.profile_shift || worm.profile_shift || 0;

        // Uncheck "use standard module" to preserve the exact module from JSON
        document.getElementById('use-standard-module').checked = false;

        // --- 4. Advanced options ---
        const profileEl = document.getElementById('profile');
        if (mfg.profile) profileEl.value = typeof mfg.profile === 'string' ? mfg.profile.toUpperCase() : mfg.profile;

        // Throated wheel
        document.getElementById('wheel-throated').checked = !!mfg.throated_wheel;

        // Stub teeth (wheel tip reduction)
        const hasStubTeeth = wheel.tip_reduction_mm != null && wheel.tip_reduction_mm > 0;
        document.getElementById('limit-wheel-od').checked = hasStubTeeth;
        document.getElementById('wheel-max-od-group').style.display = hasStubTeeth ? 'block' : 'none';
        if (hasStubTeeth) {
            document.getElementById('wheel-tip-reduction').value = wheel.tip_reduction_mm;
        }

        // --- 5. Globoid-specific ---
        if (wormType === 'globoid') {
            // Throat reduction
            const throatReductionMode = document.getElementById('throat-reduction-mode');
            if (throatReductionMode) {
                if (worm.throat_reduction_mm && worm.throat_reduction_mm > 0) {
                    throatReductionMode.value = 'custom';
                    document.getElementById('throat-reduction').value = worm.throat_reduction_mm;
                    document.getElementById('throat-reduction-custom').style.display = 'block';
                    document.getElementById('throat-reduction-auto-hint').style.display = 'none';
                } else {
                    throatReductionMode.value = 'auto';
                    document.getElementById('throat-reduction-custom').style.display = 'none';
                    document.getElementById('throat-reduction-auto-hint').style.display = 'block';
                }
            }

            // Arc angle
            const arcAngleMode = document.getElementById('arc-angle-mode');
            if (arcAngleMode) {
                if (worm.throat_arc_angle_deg && worm.throat_arc_angle_deg > 0) {
                    arcAngleMode.value = 'custom';
                    document.getElementById('arc-angle').value = worm.throat_arc_angle_deg;
                    document.getElementById('arc-angle-custom').style.display = 'block';
                    document.getElementById('arc-angle-auto-hint').style.display = 'none';
                } else {
                    arcAngleMode.value = 'auto';
                    document.getElementById('arc-angle-custom').style.display = 'none';
                    document.getElementById('arc-angle-auto-hint').style.display = 'block';
                }
            }

            // Trim to min engagement
            const trimEl = document.getElementById('trim-to-min-engagement');
            if (trimEl) trimEl.checked = !!mfg.trim_to_min_engagement;
        }

        // --- 6. Bore settings ---
        function setBore(prefix, feat) {
            const boreTypeEl = document.getElementById(`${prefix}-bore-type`);
            if (!boreTypeEl) return;

            if (!feat || feat.bore_type === 'none') {
                boreTypeEl.value = 'none';
            } else if (feat.bore_type === 'custom' && feat.bore_diameter_mm != null) {
                boreTypeEl.value = 'custom';
                document.getElementById(`${prefix}-bore-diameter`).value = feat.bore_diameter_mm;
            } else {
                // custom with null diameter = auto
                boreTypeEl.value = 'auto';
            }

            // Anti-rotation
            const antiRotEl = document.getElementById(`${prefix}-anti-rotation`);
            if (antiRotEl && feat && feat.anti_rotation) {
                antiRotEl.value = feat.anti_rotation;
            }

            // Trigger change to update visibility of custom bore / anti-rotation groups
            // (auto-fill and auto-select suppressed by _isLoading flag)
            boreTypeEl.dispatchEvent(new Event('change'));
        }

        setBore('worm', features.worm);
        setBore('wheel', features.wheel);

        // --- 7. Relief groove ---
        const reliefGroove = features.worm?.relief_groove;
        const reliefCheckbox = document.getElementById('relief-groove');
        if (reliefCheckbox) {
            reliefCheckbox.checked = !!reliefGroove;
            document.getElementById('relief-groove-group').style.display = reliefGroove ? 'block' : 'none';

            if (reliefGroove) {
                const grooveTypeEl = document.getElementById('groove-type');
                grooveTypeEl.value = reliefGroove.type || 'din76';
                grooveTypeEl.dispatchEvent(new Event('change'));

                // Set values where present, clear where null (shows placeholder "auto")
                document.getElementById('groove-width').value = reliefGroove.width_mm ?? '';
                document.getElementById('groove-depth').value = reliefGroove.depth_mm ?? '';
                document.getElementById('groove-radius').value = reliefGroove.radius_mm ?? '';
            } else {
                // Clear stale relief groove values from any previous design
                document.getElementById('groove-type').value = 'din76';
                document.getElementById('groove-width').value = '';
                document.getElementById('groove-depth').value = '';
                document.getElementById('groove-radius').value = '';
            }
        }

        // --- 8. Worm length and wheel width ---
        const hasCustomDims = (mfg.worm_length_mm != null && mfg.worm_length_mm > 0) ||
                              (mfg.wheel_width_mm != null && mfg.wheel_width_mm > 0);
        if (hasCustomDims) {
            document.getElementById('use-recommended-dims').checked = false;
            document.getElementById('custom-dims-group').style.display = 'block';
            if (mfg.worm_length_mm) document.getElementById('worm-length').value = mfg.worm_length_mm;
            if (mfg.wheel_width_mm) document.getElementById('wheel-width').value = mfg.wheel_width_mm;
        } else {
            document.getElementById('use-recommended-dims').checked = true;
            document.getElementById('custom-dims-group').style.display = 'none';
        }

        // --- 9. Preserve worm pitch diameter for round-trip fidelity ---
        // The calculator's from-module mode computes worm pitch diameter from a default
        // lead angle, which may differ from the loaded design. Store it so calculate()
        // can pass it through to preserve the original centre distance.
        const designTab2 = document.getElementById('design-tab');
        designTab2.dataset.wormPitchDiameter = worm.pitch_diameter_mm || '';

        // --- 10. Recalculate to update currentDesign, currentMarkdown, spec sheet ---
        if (getCalculatorPyodide()) {
            calculate();
        }
    } finally {
        isLoadingDesign = false;
        setLoadingState(false);
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

    const rows = buildSpecRows(design, output);

    // Helper: build a table section with inline validation messages
    function section(title, sectionRows) {
        let html = `<div class="spec-section"><h3 class="spec-section-title">${title}</h3><table class="spec-table">`;
        for (const [label, value] of sectionRows) {
            if (value === undefined || value === null) continue;
            html += `<tr><td class="spec-label">${label}</td><td class="spec-value">${value}</td></tr>`;
        }
        html += '</table>';
        html += renderInlineMessages(messages, title);
        html += '</div>';
        return html;
    }

    let html = '';

    html += section('Overview', rows.overview);
    html += section('Worm', rows.worm);
    html += section('Wheel', rows.wheel);
    html += section('Assembly', rows.assembly);

    if (rows.shaft.length > 0) {
        html += section('Shaft Interface', rows.shaft);
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

    // Also update arc angle auto hint
    const arcHint = document.getElementById('arc-angle-auto-value');
    if (arcHint && currentDesign?.worm?.throat_arc_angle_deg) {
        arcHint.textContent = `\u2248 ${currentDesign.worm.throat_arc_angle_deg.toFixed(1)}\u00b0`;
    }
}

// ============================================================================
// TAB SWITCHING
// ============================================================================

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const designTab = document.getElementById('design-tab');
    const generatorTab = document.getElementById('generator-tab');
    const previewTab = document.getElementById('preview-tab');

    // All tab content panels
    const allPanels = [designTab, generatorTab, previewTab].filter(Boolean);

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Skip disabled tabs
            if (tab.disabled) return;

            // Update active tab button
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Hide all panels
            allPanels.forEach(p => p.classList.remove('active'));

            if (targetTab === 'design') {
                designTab.classList.add('active');

                // Lazy load calculator if needed
                if (!getCalculatorPyodide()) {
                    initCalculatorTab();
                }

                // Pause preview animation when leaving
                pauseAnimation();
            } else if (targetTab === 'generator') {
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

                // Pause preview animation when leaving
                pauseAnimation();
            } else if (targetTab === 'preview') {
                previewTab.classList.add('active');

                // Auto-start viewer when tab is opened
                initPreviewViewer();
            }
        });
    });

    // Preview controls
    const playPauseBtn = document.getElementById('preview-play-pause');
    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', () => {
            const nowPlaying = togglePlayPause();
            playPauseBtn.textContent = nowPlaying ? 'Pause' : 'Play';
        });
    }

    const speedSlider = document.getElementById('preview-speed');
    const speedLabel = document.getElementById('preview-speed-label');
    if (speedSlider) {
        speedSlider.addEventListener('input', () => {
            const speed = parseFloat(speedSlider.value);
            setSpeed(speed);
            if (speedLabel) speedLabel.textContent = speed.toFixed(1) + 'x';
        });
    }
}

/**
 * Initialize and show the 3D preview viewer.
 * Auto-loads mesh data from window.generatedSTEP if available.
 */
function initPreviewViewer() {
    const canvas = document.getElementById('preview-canvas');
    const container = document.getElementById('preview-container');
    const empty = document.getElementById('preview-empty');
    const status = document.getElementById('preview-status');

    const hasMeshData = (window.generatedSTEP?.worm_3mf && window.generatedSTEP?.wheel_3mf) ||
                        (window.generatedSTEP?.worm_stl && window.generatedSTEP?.wheel_stl);
    if (!hasMeshData) {
        if (empty) empty.style.display = '';
        if (container) container.style.display = 'none';
        return;
    }

    if (empty) empty.style.display = 'none';
    if (container) container.style.display = '';

    // Initialize Three.js (idempotent)
    initViewer(canvas);
    resizeViewer(canvas);

    // Load meshes if not already loaded, or if new data is available
    if (!isLoaded()) {
        // Use the actual design JSON that was sent to the worker for generation,
        // NOT currentDesign (which is recomputed by the calculator and may have
        // different values, e.g. centre_distance if worm pitch diameter differs)
        const design = window.currentGeneratedDesign || currentDesign;
        const info = {
            centre_distance_mm: design?.assembly?.centre_distance_mm || 38,
            ratio: design?.assembly?.ratio || 30,
            num_starts: design?.worm?.num_starts || 1,
            num_teeth: design?.wheel?.num_teeth || 30,
            hand: (design?.assembly?.hand || 'right').toLowerCase(),
            mesh_rotation_deg: window.generatedSTEP.mesh_rotation_deg || 0,
        };

        // loadMeshes is async (uses JSZip for 3MF parsing)
        loadMeshes({
            worm_3mf: window.generatedSTEP.worm_3mf,
            wheel_3mf: window.generatedSTEP.wheel_3mf,
            worm_stl: window.generatedSTEP.worm_stl,
            wheel_stl: window.generatedSTEP.wheel_stl,
        }, info).catch(err => {
            console.error('[Preview] Failed to load meshes:', err);
        });

        if (status) {
            status.textContent =
                `Module ${design?.worm?.module_mm || '?'}mm | ` +
                `Ratio 1:${info.ratio} | ` +
                `Centre distance: ${info.centre_distance_mm.toFixed(1)}mm`;
        }
    }

    resumeAnimation();

    // Handle resize
    const resizeObserver = new ResizeObserver(() => resizeViewer(canvas));
    resizeObserver.observe(canvas);
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

        // If a loaded design specified a worm pitch diameter, pass it through
        // so the calculator preserves the original centre distance
        const wormPdOverride = document.getElementById('design-tab').dataset.wormPitchDiameter;
        if (wormPdOverride && mode === 'from-module') {
            inputs.worm_pitch_diameter = parseFloat(wormPdOverride);
        }

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
        currentOutput = output;
        currentValidation = output.valid;
        currentMessages = output.messages || [];
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

        // Handle worm_type from URL - set dropdown and data attribute
        if (params.has('worm_type')) {
            const wormType = params.get('worm_type');
            document.getElementById('worm-type').value = wormType;
            document.getElementById('design-tab').dataset.wormType = wormType;
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
    return createDesignFilename(currentDesign);
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
    const rows = buildSpecRows(design, currentOutput);

    const pageW = doc.internal.pageSize.getWidth();
    const margin = 15;
    const contentW = pageW - 2 * margin;
    let y = margin;

    // Colours
    const black = [30, 41, 59];
    const muted = [100, 116, 139];
    const sectionBg = [241, 245, 249];
    const borderCol = [226, 232, 240];

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

    function drawSection(title, sectionRows) {
        // Check if section fits on page (header + rows)
        const sectionH = 5.5 + sectionRows.length * 5.5 + 4;
        if (y + sectionH > 280) {
            doc.addPage();
            y = margin;
        }
        drawSectionHeader(title);
        sectionRows.forEach((row, i) => drawRow(row[0], row[1], i === sectionRows.length - 1));
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

    // Render all sections from shared row data
    drawSection('Overview', rows.overview);
    drawSection('Worm', rows.worm);
    drawSection('Wheel', rows.wheel);
    drawSection('Assembly', rows.assembly);
    if (rows.shaft.length > 0) drawSection('Shaft Interface', rows.shaft);

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
    updateGeneratorValidation(currentValidation, currentMessages);
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
                    statusEl.classList.remove('loading');
                    statusEl.classList.add('ready');
                }
                const btn = document.getElementById('generate-btn');
                if (btn) btn.disabled = false;
                break;
            case 'INIT_ERROR':
                console.error('[Generator] Initialization failed:', error);
                const statusElError = document.getElementById('generator-loading-status');
                if (statusElError) {
                    statusElError.textContent = `Error: ${error}`;
                    statusElError.classList.remove('loading');
                    statusElError.classList.add('error');
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
    updateGeneratorValidation(currentValidation, currentMessages);
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
            hideGeneratorValidation();
            syncGeneratorUI(design);
            loadDesignIntoDesignTab(design);
            appendToConsole(`Loaded ${file.name}`);
        } catch (error) {
            appendToConsole(`Error parsing ${file.name}: ${error.message}`);
        }
    };
    reader.readAsText(file);
}

/**
 * Load a JSON design file directly into the design tab.
 * Called from the "Load Definition" button on the design tab.
 */
function handleDesignFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const design = JSON.parse(e.target.result);
            if (!design.worm || !design.wheel || !design.assembly) {
                showNotification('Invalid JSON: missing worm, wheel, or assembly', true);
                return;
            }
            loadDesignIntoDesignTab(design);

            // Also update generator tab if visited
            if (generatorTabVisited) {
                document.getElementById('json-input').value = JSON.stringify(design, null, 2);
                updateDesignSummary(design);
                syncGeneratorUI(design);
            }

            showNotification(`Loaded ${file.name}`);
        } catch (error) {
            showNotification(`Error: ${error.message}`, true);
        }
    };
    reader.readAsText(file);
    // Reset input so the same file can be loaded again
    event.target.value = '';
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

    // Setup event listeners for design tab file loading
    document.getElementById('load-design-json').addEventListener('click', () => {
        document.getElementById('design-json-file-input').click();
    });
    document.getElementById('design-json-file-input').addEventListener('change', handleDesignFileUpload);

    // Setup event listeners for generator
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

    // Worm type dropdown — sync data attribute for CSS visibility rules + enforce globoid constraints
    document.getElementById('worm-type').addEventListener('change', (e) => {
        document.getElementById('design-tab').dataset.wormType = e.target.value;
        updateGenerationMethodForWormType(e.target.value);
    });

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

    // Arc angle mode switching (auto vs custom)
    document.getElementById('arc-angle-mode')?.addEventListener('change', (e) => {
        const isCustom = e.target.value === 'custom';
        document.getElementById('arc-angle-custom').style.display = isCustom ? 'block' : 'none';
        document.getElementById('arc-angle-auto-hint').style.display = isCustom ? 'none' : 'block';
        if (isCustom && currentDesign?.worm?.throat_arc_angle_deg) {
            document.getElementById('arc-angle').value = Math.round(currentDesign.worm.throat_arc_angle_deg);
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
    // Skip during JSON loading to prevent redundant intermediate calculations
    const designTab = document.getElementById('design-tab');
    const designInputs = designTab.querySelectorAll('input, select');
    designInputs.forEach(input => {
        input.addEventListener('change', () => {
            // Clear worm pitch diameter override when user manually edits any input.
            // The override is only meant for JSON round-trip fidelity — once the user
            // changes parameters, the calculator should recompute normally.
            if (!isLoadingDesign) {
                designTab.dataset.wormPitchDiameter = '';
            }
            if (getCalculatorPyodide() && !isLoadingDesign) calculate();
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
window.loadJSONFile = loadJSONFile;
window.generateGeometry = generateGeometry;
window.initGeneratorTab = initGeneratorTab;
window.openInGenerator = openInGenerator;
