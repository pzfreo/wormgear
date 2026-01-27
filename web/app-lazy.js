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
let generatorTabVisited = false;

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

        // Update UI
        updateBoreDisplaysAndDefaults(currentDesign);
        document.getElementById('results-text').textContent = output.summary;
        updateValidationUI(output.valid, output.messages);

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
    const calculatorPyodide = getCalculatorPyodide();
    if (!calculatorPyodide) return;
    const markdown = calculatorPyodide.runPython(`to_markdown(current_design, current_validation)`);
    const blob = new Blob([markdown], { type: 'text/markdown' });
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
                // Process LOG messages through progress indicator too
                handleProgress(message, null);
                break;
            case 'PROGRESS':
                handleProgress(message, percent);
                break;
            case 'GENERATE_COMPLETE':
                handleGenerateComplete(e.data);
                break;
            case 'GENERATE_ERROR':
                appendToConsole(`✗ Generation error: ${error}`);
                if (stack) console.error('Worker error stack:', stack);
                hideProgressIndicator();
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
        manufacturing: currentDesign.manufacturing
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
 */
async function cancelGeneration() {
    const generatorWorker = getGeneratorWorker();
    if (!generatorWorker) {
        return;
    }

    // Terminate the worker
    generatorWorker.terminate();

    // Append to console
    const { appendToConsole, hideProgressIndicator } = await import('./modules/generator-ui.js');
    appendToConsole('⚠️ Generation cancelled by user');

    // Hide progress and reset UI
    hideProgressIndicator();

    // Reinitialize the worker for future generations
    const { initGenerator } = await import('./modules/pyodide-init.js');
    const setupGeneratorMessageHandler = (worker) => {
        worker.addEventListener('message', async (e) => {
            const { type, message, percent } = e.data;

            switch (type) {
                case 'LOG':
                    // Process LOG messages through progress indicator too
                    handleProgress(message, null);
                    break;
                case 'PROGRESS':
                    handleProgress(message, percent);
                    break;
                case 'GENERATE_COMPLETE':
                    handleGenerateComplete(e.data);
                    break;
                case 'GENERATE_ERROR':
                    handleGenerateError(message);
                    break;
            }
        });
    };

    await initGenerator(false, setupGeneratorMessageHandler);
    appendToConsole('Ready for new generation');
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

        let wormLength = designData.worm.length_mm || manufacturing.worm_length_mm || manufacturing.worm_length || 40;
        let wheelWidth = designData.wheel.width_mm || manufacturing.wheel_width_mm || manufacturing.wheel_width;

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

    // Mode switching
    document.getElementById('mode').addEventListener('change', (e) => {
        document.querySelectorAll('.input-group').forEach(group => {
            group.style.display = group.dataset.mode === e.target.value ? 'block' : 'none';
        });
    });

    // Worm type switching (show throat reduction for globoid)
    document.getElementById('worm-type').addEventListener('change', (e) => {
        const isGloboid = e.target.value === 'globoid';
        const throatReductionGroup = document.getElementById('throat-reduction-group');
        throatReductionGroup.style.display = isGloboid ? 'block' : 'none';
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
    });

    // Use recommended dimensions toggle
    document.getElementById('use-recommended-dims').addEventListener('change', (e) => {
        const customDims = document.getElementById('custom-dims-group');
        if (customDims) {
            customDims.style.display = e.target.checked ? 'none' : 'block';
        }

        // Populate with recommended values when toggling to custom
        if (!e.target.checked && currentDesign && currentDesign.manufacturing) {
            // Note: calculator outputs worm_length_mm and wheel_width_mm (with _mm suffix)
            document.getElementById('worm-length').value = currentDesign.manufacturing.worm_length_mm || currentDesign.manufacturing.worm_length || 40;
            document.getElementById('wheel-width').value = currentDesign.manufacturing.wheel_width_mm || currentDesign.manufacturing.wheel_width || 10;
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

    // Start loading generator in background (non-blocking)
    initGeneratorTab(false).catch(err => {
        console.log('Generator background loading failed (non-fatal):', err);
    });
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
