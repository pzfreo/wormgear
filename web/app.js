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

// Update throat reduction auto hint based on geometry
// Correct formula: throat_reduction = worm_pitch_radius - (center_distance - wheel_pitch_radius)
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

        hint.textContent = `≈ ${throatReduction.toFixed(2)}mm (geometric: worm_r - (CD - wheel_r))`;
    } else {
        hint.textContent = `Calculated from worm/wheel geometry`;
    }
}

// ============================================================================
// TAB SWITCHING
// ============================================================================

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update active content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // Lazy load calculator if needed
            if (targetTab === 'calculator' && !getCalculatorPyodide()) {
                initCalculatorTab();
            }

            // Generator tab actions
            if (targetTab === 'generator') {
                // Hide progress indicator on tab switch (will be shown again when generation starts)
                const progressContainer = document.getElementById('generation-progress');
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }

                // Generator should already be loading in background (started after calculator ready)
                // If not ready yet, start it without modal - user will see status in the tab
                if (!getGeneratorWorker()) {
                    initGeneratorTab(false);  // false = no modal, load in background
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

        // Get validated inputs (throws if invalid)
        const inputs = getInputs(mode);

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
        document.getElementById('results-text').textContent = output.summary;
        updateValidationUI(output.valid, output.messages);

        // Keep generator JSON in sync if user has visited that tab
        if (generatorTabVisited) {
            document.getElementById('json-input').value = JSON.stringify(currentDesign, null, 2);
        }

    } catch (error) {
        console.error('Calculation error:', error);
        document.getElementById('results-text').textContent = `Error: ${error.message}`;
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

        // Set inputs based on mode
        params.forEach((value, key) => {
            if (key === 'mode') return;

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

function copyJSON() {
    if (!currentDesign) return;
    navigator.clipboard.writeText(JSON.stringify(currentDesign, null, 2));
    alert('JSON copied to clipboard!');
}

function downloadJSON() {
    if (!currentDesign) return;
    const blob = new Blob([JSON.stringify(currentDesign, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wormgear-design.json';
    a.click();
    URL.revokeObjectURL(url);
}

function downloadMarkdown() {
    if (!currentMarkdown) {
        alert('No design calculated yet');
        return;
    }
    const blob = new Blob([currentMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wormgear-design.md';
    a.click();
    URL.revokeObjectURL(url);
}

function copyLink() {
    const mode = document.getElementById('mode').value;
    const inputs = getInputs();
    const params = new URLSearchParams();

    params.set('mode', mode);

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
                // Generator initialization complete
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
                // Generator initialization failed
                console.error('[Generator] Initialization failed:', error);
                const statusElError = document.getElementById('generator-loading-status');
                if (statusElError) {
                    statusElError.textContent = `Error: ${error}`;
                    statusElError.style.color = '#dc3545';
                }
                break;
            case 'LOG':
                // Only show LOG messages if generation is active
                if (isGenerating) {
                    handleProgress(message, null);
                }
                break;
            case 'PROGRESS':
                // Only show PROGRESS messages if generation is active
                if (isGenerating) {
                    handleProgress(message, percent);
                }
                break;
            case 'GENERATE_COMPLETE':
                // Only process completion if generation is still active (not cancelled)
                if (isGenerating) {
                    isGenerating = false;
                    handleGenerateComplete(e.data);
                } else {
                    console.log('[Generator] Ignoring completion from cancelled generation');
                }
                break;
            case 'GENERATE_ERROR':
                // Only show error if generation is still active (not cancelled)
                if (isGenerating) {
                    isGenerating = false;
                    appendToConsole(`✗ Generation error: ${error}`);
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
        appendToConsole(`✗ Worker error: ${error.message}`);
    };
}

function loadFromCalculator() {
    if (!currentDesign) {
        alert('No design in calculator. Calculate a design first.');
        return;
    }

    // Debug: Log what's being loaded
    console.log('[DEBUG] Loading from calculator:', {
        manufacturing: currentDesign.manufacturing,
        features: currentDesign.features
    });

    document.getElementById('json-input').value = JSON.stringify(currentDesign, null, 2);
    updateDesignSummary(currentDesign);
    appendToConsole('Loaded design from calculator');

    // Also log to generator console
    if (currentDesign.manufacturing) {
        appendToConsole(`Manufacturing: Virtual Hobbing: ${currentDesign.manufacturing.virtual_hobbing || false}, Steps: ${currentDesign.manufacturing.hobbing_steps || 72}`);
    }
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
            appendToConsole(`Loaded ${file.name}`);
        } catch (error) {
            appendToConsole(`Error parsing ${file.name}: ${error.message}`);
        }
    };
    reader.readAsText(file);
}

/**
 * Cancel ongoing generation
 *
 * Note: We don't terminate the worker because that would require reloading
 * Pyodide from scratch (several minutes). Instead, we just:
 * 1. Increment the generation ID so we ignore results from the cancelled generation
 * 2. Reset the UI
 * 3. The worker continues running in the background but results are ignored
 */
async function cancelGeneration() {
    if (!isGenerating) {
        return;
    }

    // Increment generation ID - results from previous generation will be ignored
    currentGenerationId++;
    isGenerating = false;

    appendToConsole('⚠️ Generation cancelled by user');
    appendToConsole('(Background process may continue - results will be ignored)');

    // Hide progress and reset UI
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

        // Extract generation parameters from design
        const manufacturing = designData.manufacturing || {};
        const virtualHobbing = manufacturing.virtual_hobbing || false;
        const hobbingSteps = manufacturing.hobbing_steps || 72;
        const profile = manufacturing.profile || 'ZA';

        // Debug: Log what's being read from JSON
        console.log('[DEBUG] Generator reading from JSON:', {
            manufacturing: designData.manufacturing,
            virtualHobbing,
            hobbingSteps,
            profile
        });

        // Use canonical field names from schema v2.0 - no legacy fallbacks
        let wormLength = manufacturing.worm_length_mm || 40;
        let wheelWidth = manufacturing.wheel_width_mm || null;

        // Start new generation - increment ID and set flag
        currentGenerationId++;
        isGenerating = true;

        appendToConsole('Starting geometry generation...');
        appendToConsole(`Parameters: ${type}, Virtual Hobbing: ${virtualHobbing}, Profile: ${profile}`);

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
                virtualHobbing,
                hobbingSteps,
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
    initTabs();
    setupBoreEventListeners();

    // Setup event listeners for calculator (no explicit calculate button - auto-recalculates on input change)
    document.getElementById('copy-json').addEventListener('click', copyJSON);
    document.getElementById('download-json').addEventListener('click', downloadJSON);
    document.getElementById('download-md').addEventListener('click', downloadMarkdown);
    document.getElementById('copy-link').addEventListener('click', copyLink);

    // Setup event listeners for generator
    document.getElementById('load-from-calculator').addEventListener('click', loadFromCalculator);
    document.getElementById('load-json-file').addEventListener('click', loadJSONFile);
    document.getElementById('json-file-input').addEventListener('change', handleFileUpload);
    document.getElementById('generate-btn').addEventListener('click', () => generateGeometry('both'));
    document.getElementById('cancel-generate-btn').addEventListener('click', cancelGeneration);

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

    // Helper to update throat reduction visibility (globoid + helical only)
    function updateThroatReductionVisibility() {
        const isGloboid = document.getElementById('worm-type')?.value === 'globoid';
        const isHelical = document.getElementById('wheel-generation')?.value === 'helical';
        const throatReductionGroup = document.getElementById('throat-reduction-group');

        // Only show throat reduction for globoid worm with helical wheel generation
        const shouldShow = isGloboid && isHelical;
        throatReductionGroup.style.display = shouldShow ? 'block' : 'none';

        if (shouldShow) {
            updateThroatReductionAutoHint();
        }
    }

    // Worm type switching
    document.getElementById('worm-type').addEventListener('change', () => {
        updateThroatReductionVisibility();
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

    // Wheel generation method switching (helical vs virtual hobbing)
    document.getElementById('wheel-generation').addEventListener('change', (e) => {
        const isVirtualHobbing = e.target.value === 'virtual-hobbing';
        const precisionGroup = document.getElementById('hobbing-precision-group');
        const throatOptionGroup = document.getElementById('throat-option-group');

        // Show hobbing precision controls when virtual hobbing selected
        precisionGroup.style.display = isVirtualHobbing ? 'block' : 'none';

        // Hide throat option when virtual hobbing (it's automatic)
        if (isVirtualHobbing) {
            throatOptionGroup.style.display = 'none';
            document.getElementById('wheel-throated').checked = false; // Virtual hobbing handles this
        } else {
            throatOptionGroup.style.display = 'block';
        }

        // Update throat reduction visibility (only for globoid + helical)
        updateThroatReductionVisibility();
    });

    // Use recommended dimensions toggle
    document.getElementById('use-recommended-dims').addEventListener('change', (e) => {
        const customDims = document.getElementById('custom-dims-group');
        if (customDims) {
            customDims.style.display = e.target.checked ? 'none' : 'block';
        }

        // Populate with recommended values when toggling to custom
        if (!e.target.checked && currentDesign && currentDesign.manufacturing) {
            // Use canonical field names from schema v2.0 - no legacy fallbacks
            document.getElementById('worm-length').value = currentDesign.manufacturing.worm_length_mm || 40;
            document.getElementById('wheel-width').value = currentDesign.manufacturing.wheel_width_mm || 10;
        }
    });

    // Auto-recalculate on input changes
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            if (getCalculatorPyodide()) calculate();
        });
    });

    // Trigger initial UI state updates for all dynamic controls
    const wormBoreType = document.getElementById('worm-bore-type');
    const wheelBoreType = document.getElementById('wheel-bore-type');
    const wormType = document.getElementById('worm-type');
    const wheelGeneration = document.getElementById('wheel-generation');

    if (wormBoreType) wormBoreType.dispatchEvent(new Event('change'));
    if (wheelBoreType) wheelBoreType.dispatchEvent(new Event('change'));
    if (wormType) wormType.dispatchEvent(new Event('change'));
    if (wheelGeneration) wheelGeneration.dispatchEvent(new Event('change'));

    // Calculator tab is active by default, so initialize it
    initCalculatorTab();

    // Generator tab is now lazy-loaded when user clicks on it (not pre-loaded in background)
});

// Expose functions globally for HTML onclick handlers
window.calculate = calculate;
window.copyJSON = copyJSON;
window.downloadJSON = downloadJSON;
window.downloadMarkdown = downloadMarkdown;
window.copyLink = copyLink;
window.loadFromCalculator = loadFromCalculator;
window.loadJSONFile = loadJSONFile;
window.generateGeometry = generateGeometry;
window.initGeneratorTab = initGeneratorTab;
