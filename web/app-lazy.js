// Wormgear Complete Design System - Browser Application
// Refactored with modular architecture

import { calculateBoreSize, getCalculatedBores, updateBoreDisplaysAndDefaults, updateAntiRotationOptions, setupBoreEventListeners } from './modules/bore-calculator.js';
import { updateValidationUI } from './modules/validation-ui.js';
import { getDesignFunction, getInputs, formatArgs } from './modules/parameter-handler.js';
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
        const inputs = getInputs(mode);
        const func = getDesignFunction(mode);
        const args = formatArgs(inputs.calculator);
        const useStandardModule = document.getElementById('use-standard-module').checked;

        // Handle recommended dimensions
        const manufacturingSettings = {
            ...inputs.manufacturing,
            worm_length: inputs.manufacturing.use_recommended_dims ? null : inputs.manufacturing.worm_length,
            wheel_width: inputs.manufacturing.use_recommended_dims ? null : inputs.manufacturing.wheel_width
        };

        // Debug: Log manufacturing settings being sent to Python
        console.log('[DEBUG] Manufacturing settings from UI:', manufacturingSettings);

        // Set globals for Python
        calculatorPyodide.globals.set('bore_settings_dict', inputs.bore);
        calculatorPyodide.globals.set('manufacturing_settings_dict', manufacturingSettings);

        // Run calculation with module rounding
        const result = calculatorPyodide.runPython(`
import json

design = ${func}(${args})

# Check if we should round to standard module
use_standard = ${useStandardModule ? 'True' : 'False'}
mode = "${mode}"

if use_standard and mode != "from-module":
    # Get calculated module and find nearest standard
    calculated_module = design.worm.module
    standard_module = nearest_standard_module(calculated_module)

    # If different, recalculate using standard module
    if abs(calculated_module - standard_module) > 0.001:
        # For envelope mode, preserve worm pitch diameter (adjusted for addendum change)
        if mode == "envelope":
            worm_pitch_diameter = design.worm.pitch_diameter
            # Adjust for module change to maintain similar OD
            addendum_change = standard_module - calculated_module
            worm_pitch_diameter = worm_pitch_diameter - 2 * addendum_change

            design = design_from_module(
                module=standard_module,
                ratio=${inputs.calculator.ratio || 30},
                worm_pitch_diameter=worm_pitch_diameter,
                pressure_angle=${inputs.calculator.pressure_angle || 20},
                backlash=${inputs.calculator.backlash || 0},
                num_starts=${inputs.calculator.num_starts || 1},
                hand=Hand.${inputs.calculator.hand || 'RIGHT'},
                profile_shift=${inputs.calculator.profile_shift || 0},
                profile=WormProfile.${inputs.calculator.profile || 'ZA'},
                worm_type=WormType.${(inputs.calculator.worm_type || 'cylindrical').toUpperCase()},
                throat_reduction=${inputs.calculator.throat_reduction || 0.0},
                wheel_throated=${inputs.calculator.wheel_throated ? 'True' : 'False'}
            )
        else:
            # For non-envelope modes, use standard module directly
            design = design_from_module(
                module=standard_module,
                ratio=${inputs.calculator.ratio || 30},
                pressure_angle=${inputs.calculator.pressure_angle || 20},
                backlash=${inputs.calculator.backlash || 0},
                num_starts=${inputs.calculator.num_starts || 1},
                hand=Hand.${inputs.calculator.hand || 'RIGHT'},
                profile_shift=${inputs.calculator.profile_shift || 0},
                profile=WormProfile.${inputs.calculator.profile || 'ZA'},
                worm_type=WormType.${(inputs.calculator.worm_type || 'cylindrical').toUpperCase()},
                throat_reduction=${inputs.calculator.throat_reduction || 0.0},
                wheel_throated=${inputs.calculator.wheel_throated ? 'True' : 'False'}
            )

# Get settings from JavaScript BEFORE validation
bore_settings = bore_settings_dict.to_py() if 'bore_settings_dict' in dir() else None
mfg_settings = manufacturing_settings_dict.to_py() if 'manufacturing_settings_dict' in dir() else None

# Update manufacturing params with UI settings if present
# IMPORTANT: Do this BEFORE validation so the validator sees the correct virtual_hobbing flag
if mfg_settings and design.manufacturing:
    design.manufacturing.virtual_hobbing = mfg_settings.get('virtual_hobbing', False)
    design.manufacturing.hobbing_steps = mfg_settings.get('hobbing_steps', 72)

# Now validate with the updated settings
validation = validate_design(design)

globals()['current_design'] = design
globals()['current_validation'] = validation

json.dumps({
    'summary': to_summary(design),
    'json_output': to_json(design, bore_settings=bore_settings, manufacturing_settings=mfg_settings),
    'markdown': to_markdown(design, validation),
    'valid': validation.valid,
    'messages': [
        {
            'severity': m.severity.value,
            'message': m.message,
            'code': m.code,
            'suggestion': m.suggestion
        }
        for m in validation.messages
    ]
})
        `);

        const data = JSON.parse(result);
        currentDesign = typeof data.json_output === 'string' ? JSON.parse(data.json_output) : data.json_output;
        currentValidation = data.valid;

        // Debug: Log what's in the calculated design
        console.log('[DEBUG] Calculated design.manufacturing:', currentDesign.manufacturing);

        // Update UI
        updateBoreDisplaysAndDefaults(currentDesign);
        document.getElementById('results-text').textContent = data.summary;
        updateValidationUI(data.valid, data.messages);

    } catch (error) {
        console.error('Calculation error:', error);
        document.getElementById('results-text').textContent = `Error: ${error.message}`;
    }
}

function loadFromUrl() {
    // URL parameter loading (simplified for now)
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
    alert('Share link feature not yet implemented');
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

        let wormLength = designData.worm.length_mm || manufacturing.worm_length || 40;
        let wheelWidth = designData.wheel.width_mm || manufacturing.wheel_width;

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
            document.getElementById('worm-length').value = currentDesign.manufacturing.worm_length || 40;
            document.getElementById('wheel-width').value = currentDesign.manufacturing.wheel_width || 10;
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
