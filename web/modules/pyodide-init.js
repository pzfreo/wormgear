/**
 * Pyodide Initialization Module
 *
 * Handles initialization of Pyodide calculator and generator worker.
 */

let calculatorPyodide = null;
let generatorWorker = null;

/**
 * Get calculator Pyodide instance
 * @returns {object|null} Pyodide instance
 */
export function getCalculatorPyodide() {
    return calculatorPyodide;
}

/**
 * Get generator worker
 * @returns {Worker|null} Worker instance
 */
export function getGeneratorWorker() {
    return generatorWorker;
}

/**
 * Reset generator worker reference (used after terminating worker)
 */
export function resetGeneratorWorker() {
    generatorWorker = null;
}

/**
 * Enable generate button when generator is ready
 */
function enableGenerateButtons() {
    const btn = document.getElementById('generate-btn');
    if (btn) btn.disabled = false;
}

/**
 * Update loading status message
 */
function updateLoadingStatus(message) {
    const statusEl = document.getElementById('generator-loading-status');
    if (statusEl) {
        statusEl.textContent = message;
        if (message === 'Generator ready') {
            statusEl.style.color = '#22c55e';
        }
    }
}

/**
 * Initialize calculator Pyodide instance
 * @param {Function} onComplete - Callback when initialization completes
 */
export async function initCalculator(onComplete) {
    // Force reload if URL has ?reload parameter (for cache busting during development)
    const forceReload = new URLSearchParams(window.location.search).has('reload');

    if (calculatorPyodide && !forceReload) {
        if (onComplete) onComplete();
        return; // Already loaded
    }

    try {
        // Show loading screen
        document.getElementById('loading-calculator').style.display = 'flex';

        // Load Pyodide
        calculatorPyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/"
        });

        // Create directory structure
        calculatorPyodide.FS.mkdir('/home/pyodide/wormgear');
        calculatorPyodide.FS.mkdir('/home/pyodide/wormgear/calculator');
        calculatorPyodide.FS.mkdir('/home/pyodide/wormgear/io');

        // Write minimal __init__.py (don't import geometry modules for web)
        calculatorPyodide.FS.writeFile(
            '/home/pyodide/wormgear/__init__.py',
            '"""Wormgear calculator for web."""\n__version__ = "1.0.0-alpha"\n'
        );

        // Add cache buster to force reload of updated files
        const cacheBuster = Date.now();

        // Load enums module (shared types)
        const enumsResponse = await fetch(`wormgear/enums.py?v=${cacheBuster}`);
        if (!enumsResponse.ok) throw new Error(`Failed to load enums.py: ${enumsResponse.status}`);
        const enumsContent = await enumsResponse.text();
        if (enumsContent.trim().startsWith('<!DOCTYPE')) {
            throw new Error('enums.py contains HTML instead of Python code');
        }
        calculatorPyodide.FS.writeFile('/home/pyodide/wormgear/enums.py', enumsContent);

        // Load calculator module files (including js_bridge for clean JS<->Python interface)
        const calcFiles = ['__init__.py', 'core.py', 'validation.py', 'output.py', 'constants.py', 'js_bridge.py', 'json_schema.py'];
        for (const file of calcFiles) {
            const response = await fetch(`wormgear/calculator/${file}?v=${cacheBuster}`);
            if (!response.ok) throw new Error(`Failed to load calculator/${file}: ${response.status}`);
            const content = await response.text();
            if (content.trim().startsWith('<!DOCTYPE')) {
                throw new Error(`calculator/${file} contains HTML instead of Python code`);
            }
            calculatorPyodide.FS.writeFile(`/home/pyodide/wormgear/calculator/${file}`, content);
        }

        // Load core module files (bore_sizing needed by calculator)
        calculatorPyodide.FS.mkdir('/home/pyodide/wormgear/core');
        const coreFiles = ['__init__.py', 'bore_sizing.py'];
        for (const file of coreFiles) {
            const response = await fetch(`wormgear/core/${file}?v=${cacheBuster}`);
            if (!response.ok) throw new Error(`Failed to load core/${file}: ${response.status}`);
            const content = await response.text();
            if (content.trim().startsWith('<!DOCTYPE')) {
                throw new Error(`core/${file} contains HTML instead of Python code`);
            }
            calculatorPyodide.FS.writeFile(`/home/pyodide/wormgear/core/${file}`, content);
        }

        // Load io module files (dataclasses needed by calculator)
        const ioFiles = ['__init__.py', 'loaders.py', 'schema.py'];
        for (const file of ioFiles) {
            const response = await fetch(`wormgear/io/${file}?v=${cacheBuster}`);
            if (!response.ok) throw new Error(`Failed to load io/${file}: ${response.status}`);
            const content = await response.text();
            if (content.trim().startsWith('<!DOCTYPE')) {
                throw new Error(`io/${file} contains HTML instead of Python code`);
            }
            calculatorPyodide.FS.writeFile(`/home/pyodide/wormgear/io/${file}`, content);
        }

        // Load pydantic (required by io/loaders.py)
        await calculatorPyodide.loadPackage('pydantic');

        // Import unified package WITH enums
        await calculatorPyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/home/pyodide')

# Clear any cached imports to force reload of updated files
for module_name in list(sys.modules.keys()):
    if module_name.startswith('wormgear'):
        del sys.modules[module_name]

# Import the clean JS<->Python bridge (single entry point)
from wormgear.calculator.js_bridge import calculate

# Import wrapper functions that return WormGearDesign dataclass (needed for attribute access)
from wormgear.calculator import (
    calculate_design_from_module as design_from_module,
    calculate_design_from_centre_distance as design_from_centre_distance,
    calculate_design_from_wheel as design_from_wheel,
    calculate_design_from_envelope as design_from_envelope,
    nearest_standard_module,
    validate_design,
    to_json,
    to_markdown,
    to_summary
)
from wormgear.enums import Hand, WormProfile, WormType

# Legacy compatibility - allow old wormcalc imports
import wormgear.calculator as wormcalc
        `);

        // Hide loading screen
        document.getElementById('loading-calculator').style.display = 'none';

        // Enable export buttons
        document.getElementById('copy-json').disabled = false;
        document.getElementById('download-json').disabled = false;
        document.getElementById('download-md').disabled = false;
        document.getElementById('copy-link').disabled = false;

        if (onComplete) onComplete();

    } catch (error) {
        console.error('Failed to initialize calculator:', error);
        document.querySelector('#loading-calculator .loading-detail').textContent =
            `Error loading calculator: ${error.message}`;
        document.querySelector('#loading-calculator .spinner').style.display = 'none';
    }
}

/**
 * Initialize generator worker
 * @param {boolean} showModal - Whether to show loading modal
 * @param {Function} setupMessageHandler - Callback to setup message handler
 */
export async function initGenerator(showModal = true, setupMessageHandler) {
    if (generatorWorker) {
        // Already initialized, just enable buttons
        enableGenerateButtons();
        updateLoadingStatus('Generator ready');
        return;
    }

    try {
        // Show loading screen (only if not background loading)
        if (showModal) {
            document.getElementById('loading-generator').style.display = 'flex';
        }

        // Create Web Worker
        generatorWorker = new Worker('generator-worker.js');

        // Set up worker message handler (provided by caller)
        if (setupMessageHandler) {
            setupMessageHandler(generatorWorker);
        }

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

        // Hide loading overlay, enable buttons, update status
        document.getElementById('loading-generator').style.display = 'none';
        enableGenerateButtons();
        updateLoadingStatus('Generator ready');

    } catch (error) {
        console.error('Failed to initialize generator:', error);

        // Check for common WASM errors and provide helpful messages
        if (error.message.includes('WebAssembly') || error.message.includes('sentinel')) {
            const errorMessages = [
                '❌ WebAssembly instantiation failed',
                'This usually means:',
                '1. Browser lacks SharedArrayBuffer support (try Chrome/Firefox)',
                '2. CORS headers not configured (Cross-Origin-Embedder-Policy missing)',
                '3. HTTP (not HTTPS) - some features require secure context',
                '',
                '💡 Workaround: Use the Python CLI for geometry generation:',
                '   pip install build123d',
                '   pip install -e .',
                '   wormgear-geometry design.json'
            ];
            errorMessages.forEach(msg => console.error(msg));
        }

        document.querySelector('#loading-generator .loading-detail').textContent =
            `Error loading generator: ${error.message}`;
        document.querySelector('#loading-generator .spinner').style.display = 'none';
        throw error;
    }
}
