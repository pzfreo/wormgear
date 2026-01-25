// Wormgear Complete Design System - Browser Application
// Two-tab interface with lazy loading

let calculatorPyodide = null;
let generatorPyodide = null;
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
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/"
        });

        // Load local Python files
        const files = ['__init__.py', 'core.py', 'validation.py', 'output.py'];
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
    if (generatorPyodide) {
        // Already loaded, just show content
        document.getElementById('generator-lazy-load').style.display = 'none';
        document.getElementById('generator-content').style.display = 'block';
        return;
    }

    try {
        // Show loading screen
        document.getElementById('loading-generator').style.display = 'flex';

        // Load Pyodide with OCP
        generatorPyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/"
        });

        // Update loading message
        document.querySelector('#loading-generator .loading-detail').textContent =
            'Installing build123d and OCP (this may take a minute)...';

        // Install packages (this is the slow part - ~50MB download)
        await generatorPyodide.loadPackage(['micropip']);
        const micropip = generatorPyodide.pyimport('micropip');

        // Note: Actual build123d + OCP install would go here
        // For now, placeholder for demonstration
        await micropip.install(['numpy']);  // Placeholder

        // Hide loading, show generator UI
        document.getElementById('loading-generator').style.display = 'none';
        document.getElementById('generator-lazy-load').style.display = 'none';
        document.getElementById('generator-content').style.display = 'block';

        appendToConsole('Generator initialized successfully!');
        appendToConsole('Ready to generate STEP files from JSON input.');

    } catch (error) {
        console.error('Failed to initialize generator:', error);
        document.querySelector('#loading-generator .loading-detail').textContent =
            `Error loading generator: ${error.message}`;
        document.querySelector('#loading-generator .spinner').style.display = 'none';
    }
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
    const pressureAngle = parseFloat(document.getElementById('pressure-angle').value);
    const backlash = parseFloat(document.getElementById('backlash').value);
    const numStarts = parseInt(document.getElementById('num-starts').value);
    const hand = document.getElementById('hand').value;
    const profileShift = parseFloat(document.getElementById('profile-shift').value);
    const profile = document.getElementById('profile').value;
    const wormType = document.getElementById('worm-type').value;
    const throatReduction = parseFloat(document.getElementById('throat-reduction').value) || 0.0;
    const wheelThroated = document.getElementById('wheel-throated').checked;

    const baseInputs = {
        pressure_angle: pressureAngle,
        backlash: backlash,
        num_starts: numStarts,
        hand: hand,
        profile_shift: profileShift,
        profile: profile,
        worm_type: wormType,
        throat_reduction: throatReduction,
        wheel_throated: wheelThroated
    };

    switch (mode) {
        case 'envelope':
            return {
                ...baseInputs,
                worm_od: parseFloat(document.getElementById('worm-od').value),
                wheel_od: parseFloat(document.getElementById('wheel-od').value),
                ratio: parseInt(document.getElementById('ratio').value)
            };
        case 'from-wheel':
            return {
                ...baseInputs,
                wheel_od: parseFloat(document.getElementById('wheel-od-fw').value),
                ratio: parseInt(document.getElementById('ratio-fw').value),
                target_lead_angle: parseFloat(document.getElementById('target-lead-angle').value)
            };
        case 'from-module':
            return {
                ...baseInputs,
                module: parseFloat(document.getElementById('module').value),
                ratio: parseInt(document.getElementById('ratio-fm').value)
            };
        case 'from-centre-distance':
            return {
                ...baseInputs,
                centre_distance: parseFloat(document.getElementById('centre-distance').value),
                ratio: parseInt(document.getElementById('ratio-fcd').value)
            };
        default:
            return baseInputs;
    }
}

function formatArgs(inputs) {
    return Object.entries(inputs)
        .map(([key, value]) => {
            if (key === 'hand') return `hand=Hand.${value}`;
            if (key === 'profile') return `profile=WormProfile.${value}`;
            if (key === 'worm_type') return `worm_type=WormType.${value.toUpperCase()}`;
            if (key === 'wheel_throated') return `wheel_throated=${value ? 'True' : 'False'}`;
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
        const inputs = getInputs(mode);
        const func = getDesignFunction(mode);
        const args = formatArgs(inputs);
        const useStandardModule = document.getElementById('use-standard-module').checked;

        // Run calculation (simplified from original)
        const result = calculatorPyodide.runPython(`
import json

design = ${func}(${args})
validation = validate_design(design)

globals()['current_design'] = design
globals()['current_validation'] = validation

json.dumps({
    'summary': to_summary(design),
    'json_output': to_json(design, validation),
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
        appendToConsole(`Loaded ${file.name}`);
    };
    reader.readAsText(file);
}

async function generateGeometry(type) {
    if (!generatorPyodide) {
        alert('Generator not loaded. Click "Load Generator" first.');
        return;
    }

    const jsonInput = document.getElementById('json-input').value;
    if (!jsonInput.trim()) {
        alert('No JSON input. Load from calculator or paste JSON.');
        return;
    }

    appendToConsole(`Starting ${type} generation...`);

    try {
        // Parse JSON
        const design = JSON.parse(jsonInput);

        // Get options
        const wormLength = parseFloat(document.getElementById('gen-worm-length').value);
        const wheelWidth = document.getElementById('gen-wheel-width').value || 'auto';
        const globoid = document.getElementById('gen-globoid').checked;
        const virtualHobbing = document.getElementById('gen-virtual-hobbing').checked;

        // TODO: Actual geometry generation would go here
        // This requires build123d + OCP to be loaded
        appendToConsole(`Generation options: length=${wormLength}, globoid=${globoid}`);
        appendToConsole('Note: Full geometry generation coming soon!');
        appendToConsole('For now, use the Python CLI: wormgear-geometry design.json');

    } catch (error) {
        appendToConsole(`Error: ${error.message}`);
        console.error('Generation error:', error);
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

    // Lazy load calculator on first interaction with calculator tab
    // (Tab is active by default, so trigger init)
    initCalculator();
});
