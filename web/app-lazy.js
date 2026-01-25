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
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/"
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
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/",
            stdout: (text) => {
                if (text.trim()) appendToConsole(`[py] ${text}`);
            },
            stderr: (text) => {
                if (text.trim()) appendToConsole(`[py:err] ${text}`);
            }
        });

        appendToConsole('Pyodide loaded successfully');

        // Update loading message
        document.querySelector('#loading-generator .loading-detail').textContent =
            'Installing micropip...';

        // Install micropip
        await generatorPyodide.loadPackage('micropip');
        const micropip = generatorPyodide.pyimport('micropip');
        appendToConsole('micropip ready');

        // Update loading message
        document.querySelector('#loading-generator .loading-detail').textContent =
            'Installing build123d and OCP (this may take 1-2 minutes)...';

        // Install build123d and OCP using Jojain's proven method
        appendToConsole('📦 Using proven installation method from build123d-sandbox');
        appendToConsole('⏳ Large download - please be patient (2-5 minutes)...');

        const result = await generatorPyodide.runPythonAsync(`
import micropip

print("Starting package installation...")
print("Setting index URLs...")
micropip.set_index_urls(["https://yeicor.github.io/OCP.wasm", "https://pypi.org/simple"])
print("Index URLs set")

print("Installing lib3mf...")
await micropip.install("lib3mf")
print("✓ lib3mf installed")

print("Installing ssl...")
await micropip.install("ssl")
print("✓ ssl installed")

print("Installing ocp_vscode from Jojain's fork...")
await micropip.install("https://raw.githubusercontent.com/Jojain/vscode-ocp-cad-viewer/no_pyperclip/ocp_vscode-2.9.0-py3-none-any.whl")
print("✓ ocp_vscode installed")

# Mock package for build123d<0.10.0 compatibility
micropip.add_mock_package("py-lib3mf", "2.4.1", modules={"py_lib3mf": '''from lib3mf import *'''})
print("✓ Mock package added")

print("Installing build123d and sqlite3...")
await micropip.install(["build123d", "sqlite3"])
print("✓ Installation completed")

# Test imports
print("Testing imports...")
try:
    import build123d
    print(f"✓ build123d imported (version: {getattr(build123d, '__version__', 'unknown')})")
    success = True
except ImportError as e:
    print(f"✗ build123d import failed: {e}")
    success = False

"SUCCESS" if success else "FAILED"
        `);

        if (result === 'SUCCESS') {
            appendToConsole('✓ All packages installed successfully!');
            appendToConsole('✓ build123d is ready to use');

            // Load wormgear package
            await loadWormGearPackage();

            // Hide loading, show generator UI
            document.getElementById('loading-generator').style.display = 'none';
            document.getElementById('generator-lazy-load').style.display = 'none';
            document.getElementById('generator-content').style.display = 'block';

            appendToConsole('Generator initialized successfully!');
            appendToConsole('Ready to generate STEP files from JSON input.');

        } else {
            appendToConsole('⚠ Packages installed but import test failed');
            throw new Error('build123d import failed');
        }

    } catch (error) {
        console.error('Failed to initialize generator:', error);
        appendToConsole(`✗ Installation failed: ${error.message}`);

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

        // Show traceback if available
        if (generatorPyodide) {
            try {
                const tb = await generatorPyodide.runPythonAsync('import traceback; traceback.format_exc()');
                appendToConsole('');
                appendToConsole('Python traceback:');
                tb.split('\n').forEach(line => line && appendToConsole(line));
            } catch (e) {}
        }

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
    // Helper to safely parse numbers, returning null if invalid
    const safeParseFloat = (value) => {
        const parsed = parseFloat(value);
        return isNaN(parsed) ? null : parsed;
    };
    const safeParseInt = (value) => {
        const parsed = parseInt(value);
        return isNaN(parsed) ? null : parsed;
    };

    const pressureAngle = safeParseFloat(document.getElementById('pressure-angle').value);
    const backlash = safeParseFloat(document.getElementById('backlash').value);
    const numStarts = safeParseInt(document.getElementById('num-starts').value);
    const hand = document.getElementById('hand').value;
    const profileShift = safeParseFloat(document.getElementById('profile-shift').value);
    const profile = document.getElementById('profile').value;
    const wormType = document.getElementById('worm-type').value;
    const throatReduction = safeParseFloat(document.getElementById('throat-reduction').value) || 0.0;
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
                worm_od: safeParseFloat(document.getElementById('worm-od').value),
                wheel_od: safeParseFloat(document.getElementById('wheel-od').value),
                ratio: safeParseInt(document.getElementById('ratio').value)
            };
        case 'from-wheel':
            return {
                ...baseInputs,
                wheel_od: safeParseFloat(document.getElementById('wheel-od-fw').value),
                ratio: safeParseInt(document.getElementById('ratio-fw').value),
                target_lead_angle: safeParseFloat(document.getElementById('target-lead-angle').value)
            };
        case 'from-module':
            return {
                ...baseInputs,
                module: safeParseFloat(document.getElementById('module').value),
                ratio: safeParseInt(document.getElementById('ratio-fm').value)
            };
        case 'from-centre-distance':
            return {
                ...baseInputs,
                centre_distance: safeParseFloat(document.getElementById('centre-distance').value),
                ratio: safeParseInt(document.getElementById('ratio-fcd').value)
            };
        default:
            return baseInputs;
    }
}

function formatArgs(inputs) {
    return Object.entries(inputs)
        .filter(([key, value]) => value !== null && value !== undefined)  // Skip null/undefined values
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

async function loadWormGearPackage() {
    try {
        appendToConsole('Loading wormgear package...');

        // Create package directory structure
        await generatorPyodide.runPythonAsync(`
import os
import sys

# Create directory structure
os.makedirs('/home/pyodide/wormgear/core', exist_ok=True)
os.makedirs('/home/pyodide/wormgear/io', exist_ok=True)
os.makedirs('/home/pyodide/wormgear/calculator', exist_ok=True)
os.makedirs('/home/pyodide/wormgear/cli', exist_ok=True)

# Add to Python path
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
        `);

        // Define files to load with their directory structure
        const packageFiles = [
            { path: 'wormgear/__init__.py', pyPath: '/home/pyodide/wormgear/__init__.py' },
            { path: 'wormgear/core/__init__.py', pyPath: '/home/pyodide/wormgear/core/__init__.py' },
            { path: 'wormgear/core/worm.py', pyPath: '/home/pyodide/wormgear/core/worm.py' },
            { path: 'wormgear/core/wheel.py', pyPath: '/home/pyodide/wormgear/core/wheel.py' },
            { path: 'wormgear/core/features.py', pyPath: '/home/pyodide/wormgear/core/features.py' },
            { path: 'wormgear/core/globoid_worm.py', pyPath: '/home/pyodide/wormgear/core/globoid_worm.py' },
            { path: 'wormgear/core/virtual_hobbing.py', pyPath: '/home/pyodide/wormgear/core/virtual_hobbing.py' },
            { path: 'wormgear/io/__init__.py', pyPath: '/home/pyodide/wormgear/io/__init__.py' },
            { path: 'wormgear/io/loaders.py', pyPath: '/home/pyodide/wormgear/io/loaders.py' },
            { path: 'wormgear/io/schema.py', pyPath: '/home/pyodide/wormgear/io/schema.py' },
            { path: 'wormgear/calculator/__init__.py', pyPath: '/home/pyodide/wormgear/calculator/__init__.py' },
            { path: 'wormgear/calculator/core.py', pyPath: '/home/pyodide/wormgear/calculator/core.py' },
            { path: 'wormgear/calculator/validation.py', pyPath: '/home/pyodide/wormgear/calculator/validation.py' },
        ];

        let loadedCount = 0;

        for (const file of packageFiles) {
            let content = null;

            // Try to fetch from src/ (relative to web/index.html)
            try {
                const response = await fetch(`src/${file.path}`);
                if (response.ok) {
                    content = await response.text();
                }
            } catch (e) {
                console.error(`Failed to fetch ${file.path}:`, e);
            }

            if (content) {
                generatorPyodide.FS.writeFile(file.pyPath, content);
                appendToConsole(`  ✓ Loaded ${file.path}`);
                loadedCount++;
            } else {
                appendToConsole(`  ✗ Failed to load ${file.path}`);
            }
        }

        appendToConsole(`Loaded ${loadedCount}/${packageFiles.length} files`);

        if (loadedCount === 0) {
            throw new Error('No package files loaded. Run build script: cd web && ./build.sh');
        }

        // Test import
        await generatorPyodide.runPythonAsync(`
import wormgear
from wormgear.core import WormGeometry, WheelGeometry
from wormgear.io import WormParams, WheelParams, AssemblyParams
print(f"✓ wormgear package loaded (version {wormgear.__version__})")
        `);

        appendToConsole('✓ wormgear package ready');
        return true;
    } catch (error) {
        appendToConsole(`✗ Failed to load wormgear: ${error.message}`);
        console.error('Package loading error:', error);
        return false;
    }
}

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
            <tr><td><strong>Worm Type:</strong></td><td>${design.worm.throat_pitch_radius_mm ? 'Globoid (hourglass)' : 'Cylindrical'}</td></tr>
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
    if (!generatorPyodide) {
        alert('Generator not loaded. Click "Load Generator" first.');
        return;
    }

    const jsonInput = document.getElementById('json-input').value;
    if (!jsonInput.trim()) {
        alert('No JSON input. Load from calculator or paste JSON.');
        return;
    }

    const startTime = Date.now();

    try {
        // Parse JSON
        const designData = JSON.parse(jsonInput);

        // Validate structure
        if (!designData.worm || !designData.wheel || !designData.assembly) {
            appendToConsole('✗ Invalid JSON structure');
            appendToConsole('Expected format: { "worm": {...}, "wheel": {...}, "assembly": {...} }');
            return;
        }

        // Get options from UI
        const wormLength = parseFloat(document.getElementById('gen-worm-length').value) || 40;
        const wheelWidthInput = document.getElementById('gen-wheel-width').value;
        const wheelWidth = wheelWidthInput ? parseFloat(wheelWidthInput) : null;

        // Get settings from design JSON
        const manufacturing = designData.manufacturing || {};
        const isGloboid = designData.worm.throat_pitch_radius_mm !== undefined;
        const isThroated = manufacturing.throated_wheel || false;
        const profile = manufacturing.profile || 'ZA';

        appendToConsole('Starting geometry generation...');
        appendToConsole(`Parameters:`);
        appendToConsole(`  Module: ${designData.worm.module_mm} mm`);
        appendToConsole(`  Ratio: ${designData.assembly.ratio}:1`);
        appendToConsole(`  Worm length: ${wormLength} mm`);
        appendToConsole(`  Wheel width: ${wheelWidth || 'auto'} mm`);
        appendToConsole(`  Profile: ${profile} (${profile === 'ZK' ? '3D printing' : 'CNC machining'})`);
        appendToConsole(`  Worm: ${isGloboid ? 'Globoid' : 'Cylindrical'}`);
        appendToConsole(`  Wheel: ${isThroated ? 'Throated (virtual hobbing)' : 'Helical'}`);
        appendToConsole('');

        appendToConsole('⏳ Generating 3D geometry (please wait)...');
        appendToConsole('  This may take 30-90 seconds on mobile devices');

        // Pass data to Python and generate
        generatorPyodide.globals.set('design_json_str', JSON.stringify(designData));
        generatorPyodide.globals.set('worm_length', wormLength);
        generatorPyodide.globals.set('wheel_width_val', wheelWidth || null);
        generatorPyodide.globals.set('throated_val', isThroated);
        generatorPyodide.globals.set('generate_type', type);

        const pythonStartTime = Date.now();
        const result = await generatorPyodide.runPythonAsync(`
import json
import base64
import tempfile
import os
from wormgear.core import WormGeometry, WheelGeometry
from wormgear.io import WormParams, WheelParams, AssemblyParams

print("📋 Parsing parameters...")
# Parse design JSON
design_data = json.loads(design_json_str)

# Create parameter objects
worm_params = WormParams(**design_data['worm'])
wheel_params = WheelParams(**design_data['wheel'])
assembly_params = AssemblyParams(**design_data['assembly'])

# Handle None wheel_width
try:
    wheel_width = float(wheel_width_val) if wheel_width_val else None
except (TypeError, ValueError):
    wheel_width = None
print(f"Wheel width: {wheel_width if wheel_width else 'auto-calculated'}")
print(f"Worm length (from JS): {worm_length}")

print("✓ Parameters parsed")
print("")

worm_b64 = None
wheel_b64 = None

# Generate worm if requested
if generate_type in ['worm', 'both']:
    print("🔩 Generating worm gear...")
    try:
        print("  Creating worm geometry object...")
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=worm_length,
            sections_per_turn=36
        )
        print("  Building 3D model...")
        worm = worm_geo.build()
        print("  Exporting to STEP format...")

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.step', delete=False) as tmp:
            temp_path = tmp.name

        worm_geo.export_step(temp_path)

        # Read back as bytes
        with open(temp_path, 'rb') as f:
            worm_step = f.read()

        # Clean up temp file
        os.unlink(temp_path)

        worm_b64 = base64.b64encode(worm_step).decode('utf-8')

        size_kb = len(worm_step) / 1024
        print(f"✓ Worm generated successfully!")
        print(f"  File size: {size_kb:.1f} KB ({len(worm_step)} bytes)")
    except Exception as e:
        print(f"✗ Worm generation failed: {e}")
        import traceback
        traceback.print_exc()

    print("")

# Generate wheel if requested
if generate_type in ['wheel', 'both']:
    print("⚙️  Generating wheel gear...")
    try:
        print("  Creating wheel geometry object...")
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=wheel_width,
            throated=throated_val
        )
        print("  Building 3D model (this is the slowest step)...")
        wheel = wheel_geo.build()
        print("  Exporting to STEP format...")

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.step', delete=False) as tmp:
            temp_path = tmp.name

        wheel_geo.export_step(temp_path)

        # Read back as bytes
        with open(temp_path, 'rb') as f:
            wheel_step = f.read()

        # Clean up temp file
        os.unlink(temp_path)

        wheel_b64 = base64.b64encode(wheel_step).decode('utf-8')

        size_kb = len(wheel_step) / 1024
        print(f"✓ Wheel generated successfully!")
        print(f"  File size: {size_kb:.1f} KB ({len(wheel_step)} bytes)")
    except Exception as e:
        print(f"✗ Wheel generation failed: {e}")
        import traceback
        traceback.print_exc()

    print("")

# Report results
if generate_type == 'worm' and worm_b64:
    print("✅ Worm generated successfully!")
elif generate_type == 'wheel' and wheel_b64:
    print("✅ Wheel generated successfully!")
elif generate_type == 'both':
    if worm_b64 and wheel_b64:
        print("✅ Both parts generated successfully!")
    elif worm_b64:
        print("⚠️  Only worm generated (wheel failed)")
    elif wheel_b64:
        print("⚠️  Only wheel generated (worm failed)")
    else:
        print("❌ Both parts failed to generate")

# Return results
{
    'worm': worm_b64,
    'wheel': wheel_b64,
    'success': (generate_type == 'worm' and worm_b64 is not None) or
               (generate_type == 'wheel' and wheel_b64 is not None) or
               (generate_type == 'both' and worm_b64 is not None and wheel_b64 is not None)
}
        `);

        const pythonElapsed = ((Date.now() - pythonStartTime) / 1000).toFixed(1);
        appendToConsole(`✓ Python execution completed (${pythonElapsed}s)`);
        appendToConsole('');

        // Process results
        appendToConsole('⏳ Processing results...');
        const resultObj = result.toJs({ dict_converter: Object.fromEntries });

        appendToConsole(`Result status: ${resultObj.success ? 'SUCCESS' : 'FAILED'}`);
        appendToConsole(`Worm data: ${resultObj.worm ? 'Present' : 'Missing'}`);
        appendToConsole(`Wheel data: ${resultObj.wheel ? 'Present' : 'Missing'}`);

        if (resultObj.success) {
            appendToConsole('');
            appendToConsole('✓ Geometry generated successfully!');

            // Download files
            if (resultObj.worm && type !== 'wheel') {
                appendToConsole('📥 Triggering worm.step download...');
                downloadSTEP('worm.step', resultObj.worm);
                appendToConsole('✓ Worm STEP file download triggered');
            }

            if (resultObj.wheel && type !== 'worm') {
                appendToConsole('📥 Triggering wheel.step download...');
                downloadSTEP('wheel.step', resultObj.wheel);
                appendToConsole('✓ Wheel STEP file download triggered');
            }

            const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            appendToConsole('');
            appendToConsole(`✅ Generation complete! Total time: ${totalElapsed}s`);
            appendToConsole('📁 Check your downloads folder for STEP files');

        } else {
            appendToConsole('');
            appendToConsole('❌ Generation failed - check messages above for details');
        }

    } catch (error) {
        appendToConsole('');
        appendToConsole(`❌ Error: ${error.message}`);
        console.error('Generation error:', error);

        // Show Python traceback if available
        try {
            const tb = await generatorPyodide.runPythonAsync('import traceback; traceback.format_exc()');
            if (tb && tb !== 'NoneType: None\n') {
                appendToConsole('Python traceback:');
                tb.split('\n').forEach(line => line && appendToConsole(line));
            }
        } catch (e) {
            console.error('Could not get Python traceback:', e);
        }
    }
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
