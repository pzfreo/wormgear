// Wormgear Complete Design System - Browser Application
// Two-tab interface with lazy loading

let calculatorPyodide = null;
let generatorPyodide = null;  // Deprecated - kept for compatibility
let generatorWorker = null;  // Web Worker for geometry generation
let currentDesign = null;
let currentValidation = null;

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
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // Lazy load calculator if needed
            if (targetTab === 'calculator' && !calculatorPyodide) {
                initCalculator();
            }
        });
    });
}

// ============================================================================
// CALCULATOR - LAZY LOADING
// ============================================================================

async function initCalculator() {
    if (calculatorPyodide) return; // Already loaded

    try {
        // Show loading screen
        document.getElementById('loading-calculator').style.display = 'flex';

        // Load Pyodide
        calculatorPyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/"
        });

        // Load local Python files
        const files = ['__init__.py', 'core.py', 'validation.py', 'output.py', 'js_bridge.py', 'json_schema.py'];
        calculatorPyodide.FS.mkdir('/home/pyodide/wormcalc');

        for (const file of files) {
            const response = await fetch(`wormcalc/${file}`);
            if (!response.ok) {
                throw new Error(`Failed to load ${file}: ${response.status}`);
            }
            const content = await response.text();
            if (content.trim().startsWith('<!DOCTYPE')) {
                throw new Error(`${file} contains HTML instead of Python code`);
            }
            calculatorPyodide.FS.writeFile(`/home/pyodide/wormcalc/${file}`, content);
        }

        // Import module
        await calculatorPyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/home/pyodide')
import wormcalc
from wormcalc import (
    design_from_envelope,
    design_from_wheel,
    design_from_module,
    design_from_centre_distance,
    validate_design,
    to_json,
    to_markdown,
    to_summary,
    nearest_standard_module,
    Hand,
    WormProfile,
    WormType
)
        `);

        // Hide loading screen
        document.getElementById('loading-calculator').style.display = 'none';

        // Enable export buttons
        document.getElementById('copy-json').disabled = false;
        document.getElementById('download-json').disabled = false;
        document.getElementById('download-md').disabled = false;
        document.getElementById('copy-link').disabled = false;

        // Load from URL parameters if present
        loadFromUrl();

        // Initial calculation
        calculate();

    } catch (error) {
        console.error('Failed to initialize calculator:', error);
        document.querySelector('#loading-calculator .loading-detail').textContent =
            `Error loading calculator: ${error.message}`;
        document.querySelector('#loading-calculator .spinner').style.display = 'none';
    }
}

// ============================================================================
// GENERATOR - LAZY LOADING
// ============================================================================

async function initGenerator() {
    if (generatorWorker) {
        // Already initialized, just show content
        document.getElementById('generator-lazy-load').style.display = 'none';
        document.getElementById('generator-content').style.display = 'block';
        return;
    }

    try {
        // Show loading screen
        document.getElementById('loading-generator').style.display = 'flex';

        // Create Web Worker
        appendToConsole('🚀 Initializing generator in background thread...');
        appendToConsole('   UI will stay responsive during loading');
        generatorWorker = new Worker('generator-worker.js');

        // Set up worker message handler
        setupWorkerMessageHandler();

        // Send initialization message
        generatorWorker.postMessage({ type: 'INIT' });

        // Wait for initialization to complete
        await new Promise((resolve, reject) => {
            const handleInit = (e) => {
                if (e.data.type === 'INIT_COMPLETE') {
                    generatorWorker.removeEventListener('message', handleInit);
                    resolve();
                } else if (e.data.type === 'INIT_ERROR') {
                    generatorWorker.removeEventListener('message', handleInit);
                    reject(new Error(e.data.error));
                }
            };
            generatorWorker.addEventListener('message', handleInit);
        });

        // Hide loading, show generator UI
        document.getElementById('loading-generator').style.display = 'none';
        document.getElementById('generator-lazy-load').style.display = 'none';
        document.getElementById('generator-content').style.display = 'block';

    } catch (error) {
        console.error('Failed to initialize generator:', error);
        appendToConsole(`✗ Initialization failed: ${error.message}`);

        // Check for common WASM errors
        if (error.message.includes('WebAssembly') || error.message.includes('sentinel')) {
            appendToConsole('');
            appendToConsole('❌ WebAssembly instantiation failed');
            appendToConsole('This usually means:');
            appendToConsole('1. Browser lacks SharedArrayBuffer support (try Chrome/Firefox)');
            appendToConsole('2. CORS headers not configured (Cross-Origin-Embedder-Policy missing)');
            appendToConsole('3. HTTP (not HTTPS) - some features require secure context');
            appendToConsole('');
            appendToConsole('💡 Workaround: Use the Python CLI for geometry generation:');
            appendToConsole('   pip install build123d');
            appendToConsole('   pip install -e .');
            appendToConsole('   wormgear-geometry design.json');
        }

        document.querySelector('#loading-generator .loading-detail').textContent =
            `Error loading generator: ${error.message}`;
        document.querySelector('#loading-generator .spinner').style.display = 'none';
    }
}

function setupWorkerMessageHandler() {
    generatorWorker.onmessage = (e) => {
        const { type, message, percent, error, stack } = e.data;

        switch (type) {
            case 'LOG':
                appendToConsole(message);
                break;

            case 'PROGRESS':
                handleProgress(message, percent);
                break;

            case 'GENERATE_COMPLETE':
                handleGenerateComplete(e.data);
                break;

            case 'GENERATE_ERROR':
                appendToConsole(`✗ Generation error: ${error}`);
                if (stack) {
                    console.error('Worker error stack:', stack);
                }
                hideProgressIndicator();
                break;

            case 'INIT_ERROR':
                // Handled in initGenerator promise
                break;
        }
    };

    generatorWorker.onerror = (error) => {
        console.error('Worker error:', error);
        appendToConsole(`✗ Worker error: ${error.message}`);
    };
}

function appendToConsole(message) {
    const console = document.getElementById('console-output');
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    console.appendChild(line);
    console.scrollTop = console.scrollHeight;
}

// ============================================================================
// CALCULATOR LOGIC (from original app.js)
// ============================================================================

function getDesignFunction(mode) {
    const functions = {
        'envelope': 'design_from_envelope',
        'from-wheel': 'design_from_wheel',
        'from-module': 'design_from_module',
        'from-centre-distance': 'design_from_centre_distance',
    };
    return functions[mode];
}

function getInputs(mode) {
    // Helper to safely parse numbers, returning null if invalid
    const safeParseFloat = (value) => {
        const parsed = parseFloat(value);
        return isNaN(parsed) ? null : parsed;
    };
    const safeParseInt = (value) => {
        const parsed = parseInt(value);
        return isNaN(parsed) ? null : parsed;
    };

    // Calculator parameters only (passed to Python calculation functions)
    const calculatorParams = {
        pressure_angle: safeParseFloat(document.getElementById('pressure-angle').value),
        backlash: safeParseFloat(document.getElementById('backlash').value),
        num_starts: safeParseInt(document.getElementById('num-starts').value),
        hand: document.getElementById('hand').value,
        profile_shift: safeParseFloat(document.getElementById('profile-shift').value),
        profile: document.getElementById('profile').value,
        worm_type: document.getElementById('worm-type').value,
        throat_reduction: safeParseFloat(document.getElementById('throat-reduction').value) || 0.0,
        wheel_throated: document.getElementById('wheel-throated').checked
    };

    // Add mode-specific calculator parameters
    switch (mode) {
        case 'envelope':
            calculatorParams.worm_od = safeParseFloat(document.getElementById('worm-od').value);
            calculatorParams.wheel_od = safeParseFloat(document.getElementById('wheel-od').value);
            calculatorParams.ratio = safeParseInt(document.getElementById('ratio').value);
            break;
        case 'from-wheel':
            calculatorParams.wheel_od = safeParseFloat(document.getElementById('wheel-od-fw').value);
            calculatorParams.ratio = safeParseInt(document.getElementById('ratio-fw').value);
            calculatorParams.target_lead_angle = safeParseFloat(document.getElementById('target-lead-angle').value);
            break;
        case 'from-module':
            calculatorParams.module = safeParseFloat(document.getElementById('module').value);
            calculatorParams.ratio = safeParseInt(document.getElementById('ratio-fm').value);
            break;
        case 'from-centre-distance':
            calculatorParams.centre_distance = safeParseFloat(document.getElementById('centre-distance').value);
            calculatorParams.ratio = safeParseInt(document.getElementById('ratio-fcd').value);
            break;
    }

    // Manufacturing parameters (for JSON export, not calculation)
    const wheelGeneration = document.getElementById('wheel-generation').value;
    const hobbingPrecision = document.getElementById('hobbing-precision').value;
    const hobbingStepsMap = {
        'preview': 36,
        'balanced': 72,
        'high': 144
    };

    const manufacturingParams = {
        virtual_hobbing: wheelGeneration === 'virtual-hobbing',
        hobbing_steps: hobbingStepsMap[hobbingPrecision] || 72,
        use_recommended_dims: document.getElementById('use-recommended-dims').checked,
        worm_length: safeParseFloat(document.getElementById('worm-length').value),
        wheel_width: safeParseFloat(document.getElementById('wheel-width').value)
    };

    // Bore/keyway parameters (for JSON export, not calculation)
    const boreParams = {
        worm_bore_type: document.getElementById('worm-bore-type').value,
        worm_bore_diameter: safeParseFloat(document.getElementById('worm-bore-diameter').value),
        worm_keyway: document.getElementById('worm-keyway').value,
        wheel_bore_type: document.getElementById('wheel-bore-type').value,
        wheel_bore_diameter: safeParseFloat(document.getElementById('wheel-bore-diameter').value),
        wheel_keyway: document.getElementById('wheel-keyway').value
    };

    return {
        calculator: calculatorParams,
        manufacturing: manufacturingParams,
        bore: boreParams
    };
}

function formatArgs(calculatorParams) {
    // Convert calculator parameters to Python function call arguments
    // Receives only calculator params - no filtering needed (clean boundary!)
    return Object.entries(calculatorParams)
        .filter(([key, value]) => value !== null && value !== undefined)
        .map(([key, value]) => {
            // Enum conversions
            if (key === 'hand') return `hand=Hand.${value}`;
            if (key === 'profile') return `profile=WormProfile.${value}`;
            if (key === 'worm_type') return `worm_type=WormType.${value.toUpperCase()}`;
            // Boolean conversion
            if (typeof value === 'boolean') return `${key}=${value ? 'True' : 'False'}`;
            // Numeric/string values
            return `${key}=${value}`;
        })
        .join(', ');
}

function calculate() {
    if (!calculatorPyodide) {
        // Not ready yet, trigger lazy load
        initCalculator();
        return;
    }

    try {
        const mode = document.getElementById('mode').value;
        const inputs = getInputs(mode);  // Returns {calculator, manufacturing, bore}
        const func = getDesignFunction(mode);
        const args = formatArgs(inputs.calculator);  // Only calculator params
        const useStandardModule = document.getElementById('use-standard-module').checked;

        // Handle recommended dimensions in manufacturing settings
        const manufacturingSettings = {
            ...inputs.manufacturing,
            worm_length: inputs.manufacturing.use_recommended_dims ? null : inputs.manufacturing.worm_length,
            wheel_width: inputs.manufacturing.use_recommended_dims ? null : inputs.manufacturing.wheel_width
        };

        // Set as globals so Python can access them (will be validated at boundary)
        calculatorPyodide.globals.set('bore_settings_dict', inputs.bore);
        calculatorPyodide.globals.set('manufacturing_settings_dict', manufacturingSettings);

        // Run calculation (simplified from original)
        const result = calculatorPyodide.runPython(`
import json

design = ${func}(${args})
validation = validate_design(design)

globals()['current_design'] = design
globals()['current_validation'] = validation

# Get settings from JavaScript
bore_settings = bore_settings_dict.to_py() if 'bore_settings_dict' in dir() else None
mfg_settings = manufacturing_settings_dict.to_py() if 'manufacturing_settings_dict' in dir() else None

# Update manufacturing params with UI settings if present
if mfg_settings and design.manufacturing:
    design.manufacturing.virtual_hobbing = mfg_settings.get('virtual_hobbing', False)
    design.manufacturing.hobbing_steps = mfg_settings.get('hobbing_steps', 72)

json.dumps({
    'summary': to_summary(design),
    'json_output': to_json(design, validation, bore_settings=bore_settings, manufacturing_settings=mfg_settings),
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
        currentDesign = data.json_output;
        currentValidation = data.valid;

        // Update UI
        document.getElementById('results-text').textContent = data.summary;
        updateValidationUI(data.valid, data.messages);

    } catch (error) {
        console.error('Calculation error:', error);
        document.getElementById('results-text').textContent = `Error: ${error.message}`;
    }
}

function updateValidationUI(valid, messages) {
    const statusDiv = document.getElementById('validation-status');
    const messagesList = document.getElementById('validation-messages');

    statusDiv.className = valid ? 'status-valid' : 'status-error';
    statusDiv.textContent = valid ? '✓ Design valid' : '✗ Design has errors';

    messagesList.innerHTML = '';
    messages.forEach(msg => {
        const li = document.createElement('li');
        li.className = `validation-${msg.severity}`;
        li.innerHTML = `<strong>${msg.code}</strong>: ${msg.message}`;
        if (msg.suggestion) {
            li.innerHTML += `<br><em>Suggestion: ${msg.suggestion}</em>`;
        }
        messagesList.appendChild(li);
    });
}

function loadFromUrl() {
    // URL parameter loading logic (from original app.js)
    // Simplified for now
}

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

function copyJSON() {
    if (!currentDesign) return;
    navigator.clipboard.writeText(currentDesign);
    alert('JSON copied to clipboard!');
}

function downloadJSON() {
    if (!currentDesign) return;
    const blob = new Blob([currentDesign], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wormgear-design.json';
    a.click();
    URL.revokeObjectURL(url);
}

function downloadMarkdown() {
    if (!calculatorPyodide) return;
    const markdown = calculatorPyodide.runPython(`
to_markdown(current_design, current_validation)
    `);
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wormgear-design.md';
    a.click();
    URL.revokeObjectURL(url);
}

function copyLink() {
    // Generate shareable URL (from original app.js)
    alert('Share link feature not yet implemented');
}

// ============================================================================
// GENERATOR FUNCTIONS
// ============================================================================

function loadFromCalculator() {
    if (!currentDesign) {
        alert('No design in calculator. Calculate a design first.');
        return;
    }
    document.getElementById('json-input').value = currentDesign;
    updateDesignSummary(JSON.parse(currentDesign));
    appendToConsole('Loaded design from calculator');
}

function updateDesignSummary(design) {
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

async function generateGeometry(type) {
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
        // Parse JSON
        const designData = JSON.parse(jsonInput);

        // Validate structure
        if (!designData.worm || !designData.wheel || !designData.assembly) {
            appendToConsole('Invalid JSON structure');
            appendToConsole('Expected format: { "worm": {...}, "wheel": {...}, "assembly": {...} }');
            return;
        }

        // Get settings from design JSON
        const manufacturing = designData.manufacturing || {};
        const isGloboid = designData.worm.throat_curvature_radius_mm !== undefined;
        const virtualHobbing = manufacturing.virtual_hobbing || false;
        const hobbingSteps = manufacturing.hobbing_steps || 72;
        const profile = manufacturing.profile || 'ZA';

        // Get dimensions from calculator settings (or use defaults)
        let wormLength = designData.worm.length_mm;
        if (!wormLength && manufacturing.worm_length) {
            wormLength = manufacturing.worm_length;
        }
        if (!wormLength) {
            wormLength = 40; // Fallback default
        }

        // Wheel width - prefer design value, then manufacturing recommendation, then null (auto)
        let wheelWidth = designData.wheel.width_mm;
        if (!wheelWidth && manufacturing.wheel_width) {
            wheelWidth = manufacturing.wheel_width;
        }

        appendToConsole('Starting geometry generation...');
        appendToConsole('Parameters:');
        appendToConsole('  Module: ' + designData.worm.module_mm + ' mm');
        appendToConsole('  Ratio: ' + designData.assembly.ratio + ':1');
        appendToConsole('  Worm length: ' + wormLength + ' mm');
        appendToConsole('  Wheel width: ' + (wheelWidth || 'auto') + ' mm');
        appendToConsole('  Profile: ' + profile);
        appendToConsole('  Worm: ' + (isGloboid ? 'Globoid' : 'Cylindrical'));
        appendToConsole('  Wheel: ' + (virtualHobbing ? 'Virtual Hobbing (' + hobbingSteps + ' steps)' : 'Helical'));
        appendToConsole('');

        appendToConsole('Generating 3D geometry in background thread...');
        appendToConsole('UI will remain responsive during generation');

        // Show progress indicator
        showProgressIndicator();

        // Send generation request to worker
        generatorWorker.postMessage({
            type: 'GENERATE',
            data: {
                designData,
                wormLength,
                wheelWidth,
                virtualHobbing,
                hobbingSteps,
                generateType: type
            }
        });

    } catch (error) {
        appendToConsole('Error: ' + error.message);
        console.error('Generation error:', error);
        hideProgressIndicator();
    }
}

function handleProgress(message, percent) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    // Update progress bar
    if (percent >= 0 && percent <= 100) {
        progressBar.style.width = percent + '%';
        progressBar.textContent = percent.toFixed(0) + '%';
    }
    progressText.textContent = message;

    // Update console (throttled for performance)
    if (!handleProgress.lastUpdate) handleProgress.lastUpdate = 0;
    const now = Date.now();
    if (now - handleProgress.lastUpdate > 500 || percent >= 100 || percent < 0) {
        appendToConsole('  [' + percent.toFixed(0) + '%] ' + message);
        handleProgress.lastUpdate = now;
    }
}

function handleGenerateComplete(data) {
    const { success, worm, wheel } = data;

    appendToConsole('');
    appendToConsole('Generation complete!');

    if (success) {
        const generateType = worm && wheel ? 'both' : (worm ? 'worm' : 'wheel');

        if (worm) {
            downloadSTEP('worm.step', worm);
        }
        if (wheel) {
            downloadSTEP('wheel.step', wheel);
        }

        appendToConsole('');
        appendToConsole(generateType + ' generated successfully!');
    } else {
        appendToConsole('Generation completed with errors - see console above');
    }

    hideProgressIndicator();
}

function showProgressIndicator() {
    const progressContainer = document.getElementById('generation-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressText.textContent = 'Initializing...';
}

function hideProgressIndicator() {
    const progressContainer = document.getElementById('generation-progress');
    progressContainer.style.display = 'none';
}


// Download STEP file from base64
function downloadSTEP(filename, base64Data) {
    try {
        appendToConsole(`  Decoding ${filename}...`);
        // Decode base64 to binary
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        const sizeKB = (bytes.length / 1024).toFixed(1);
        appendToConsole(`  File size: ${sizeKB} KB (${bytes.length} bytes)`);

        // Create blob and download
        appendToConsole(`  Creating download blob...`);
        const blob = new Blob([bytes], { type: 'application/step' });
        const url = URL.createObjectURL(blob);

        appendToConsole(`  Triggering browser download for ${filename}...`);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);

        // Click to trigger download
        a.click();

        // Cleanup
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            appendToConsole(`  Download complete: ${filename}`);
        }, 100);

    } catch (error) {
        appendToConsole(`❌ Download failed for ${filename}: ${error.message}`);
        console.error('Download error:', error);
    }
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize tabs
    initTabs();

    // Mode switching
    document.getElementById('mode').addEventListener('change', (e) => {
        document.querySelectorAll('.input-group').forEach(group => {
            group.style.display = group.dataset.mode === e.target.value ? 'block' : 'none';
        });
        if (calculatorPyodide) calculate();
    });

    // Worm type switching
    document.getElementById('worm-type').addEventListener('change', (e) => {
        const throatGroup = document.getElementById('throat-reduction-group');
        throatGroup.style.display = e.target.value === 'globoid' ? 'block' : 'none';
    });

    // Wheel generation switching
    document.getElementById('wheel-generation').addEventListener('change', (e) => {
        const isVirtualHobbing = e.target.value === 'virtual-hobbing';
        const precisionGroup = document.getElementById('hobbing-precision-group');
        const throatOptionGroup = document.getElementById('throat-option-group');

        precisionGroup.style.display = isVirtualHobbing ? 'block' : 'none';

        // Hide throat option when virtual hobbing (it's automatic)
        if (isVirtualHobbing) {
            throatOptionGroup.style.display = 'none';
            document.getElementById('wheel-throated').checked = false; // Virtual hobbing handles this
        } else {
            throatOptionGroup.style.display = 'block';
        }
    });

    // Use recommended dimensions switching
    document.getElementById('use-recommended-dims').addEventListener('change', (e) => {
        const customDimsGroup = document.getElementById('custom-dims-group');
        customDimsGroup.style.display = e.target.checked ? 'none' : 'block';
    });

    // Worm bore type switching
    document.getElementById('worm-bore-type').addEventListener('change', (e) => {
        const customGroup = document.getElementById('worm-bore-custom');
        const keywayGroup = document.getElementById('worm-keyway-group');
        const hasBore = e.target.value !== 'none';

        customGroup.style.display = e.target.value === 'custom' ? 'block' : 'none';
        keywayGroup.style.display = hasBore ? 'block' : 'none';
    });

    // Wheel bore type switching
    document.getElementById('wheel-bore-type').addEventListener('change', (e) => {
        const customGroup = document.getElementById('wheel-bore-custom');
        const keywayGroup = document.getElementById('wheel-keyway-group');
        const hasBore = e.target.value !== 'none';

        customGroup.style.display = e.target.value === 'custom' ? 'block' : 'none';
        keywayGroup.style.display = hasBore ? 'block' : 'none';
    });

    // Input changes trigger recalculation
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            if (calculatorPyodide) calculate();
        });
    });

    // Export buttons
    document.getElementById('copy-json').addEventListener('click', copyJSON);
    document.getElementById('download-json').addEventListener('click', downloadJSON);
    document.getElementById('download-md').addEventListener('click', downloadMarkdown);
    document.getElementById('copy-link').addEventListener('click', copyLink);

    // Generator buttons
    document.getElementById('load-generator-btn').addEventListener('click', initGenerator);
    document.getElementById('load-from-calculator').addEventListener('click', loadFromCalculator);
    document.getElementById('load-json-file').addEventListener('click', loadJSONFile);
    document.getElementById('json-file-input').addEventListener('change', handleFileUpload);
    document.getElementById('generate-worm-btn').addEventListener('click', () => generateGeometry('worm'));
    document.getElementById('generate-wheel-btn').addEventListener('click', () => generateGeometry('wheel'));
    document.getElementById('generate-both-btn').addEventListener('click', () => generateGeometry('both'));

    // Trigger initial UI state updates
    document.getElementById('worm-bore-type').dispatchEvent(new Event('change'));
    document.getElementById('wheel-bore-type').dispatchEvent(new Event('change'));

    // Lazy load calculator on first interaction with calculator tab
    // (Tab is active by default, so trigger init)
    initCalculator();
});
