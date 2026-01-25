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
    if (calculatorPyodide) {
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
