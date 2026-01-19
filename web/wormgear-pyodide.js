/**
 * Worm Gear Geometry - Pyodide Integration
 *
 * This module handles loading the wormgear_geometry package into Pyodide
 * and provides functions for generating geometry in the browser.
 */

/**
 * Load the wormgear_geometry package from the local source directory
 * @param {object} pyodide - Initialized Pyodide instance
 * @returns {Promise<boolean>} - Success status
 */
export async function loadWormGearPackage(pyodide) {
    try {
        console.log('Loading wormgear_geometry package...');

        // First, we need to fetch all Python files from ../src/wormgear_geometry/
        const packageFiles = [
            '__init__.py',
            'io.py',
            'worm.py',
            'wheel.py',
            'features.py',
            'cli.py'
        ];

        // Create the package directory in Pyodide's virtual filesystem
        await pyodide.runPythonAsync(`
import os
os.makedirs('/home/pyodide/wormgear_geometry', exist_ok=True)
import sys
sys.path.insert(0, '/home/pyodide')
        `);

        // Fetch and write each file
        for (const filename of packageFiles) {
            try {
                const response = await fetch(`../src/wormgear_geometry/${filename}`);
                if (!response.ok) {
                    console.warn(`Could not load ${filename}: ${response.status}`);
                    continue;
                }

                const content = await response.text();

                // Write file to Pyodide filesystem
                pyodide.FS.writeFile(
                    `/home/pyodide/wormgear_geometry/${filename}`,
                    content
                );

                console.log(`  ✓ Loaded ${filename}`);
            } catch (error) {
                console.warn(`  ✗ Failed to load ${filename}:`, error);
            }
        }

        // Try to import the package
        await pyodide.runPythonAsync(`
try:
    import wormgear_geometry
    print(f"wormgear_geometry package imported successfully")
    print(f"Available: {dir(wormgear_geometry)}")
except ImportError as e:
    print(f"Failed to import wormgear_geometry: {e}")
    raise
        `);

        console.log('✓ wormgear_geometry package loaded successfully');
        return true;

    } catch (error) {
        console.error('Failed to load wormgear_geometry package:', error);
        return false;
    }
}

/**
 * Generate worm and wheel geometry from design JSON
 * @param {object} pyodide - Initialized Pyodide instance
 * @param {object} designData - Design JSON from wormgearcalc
 * @param {object} options - Generation options
 * @returns {Promise<object>} - Generated files
 */
export async function generateGeometry(pyodide, designData, options = {}) {
    const {
        wormLength = 40,
        wheelWidth = null,
        throated = false,
        addBore = false,
        addKeyway = false
    } = options;

    try {
        // Pass the design data to Python
        pyodide.globals.set('design_json', JSON.stringify(designData));
        pyodide.globals.set('worm_length', wormLength);
        pyodide.globals.set('wheel_width', wheelWidth);
        pyodide.globals.set('throated', throated);
        pyodide.globals.set('add_bore', addBore);
        pyodide.globals.set('add_keyway', addKeyway);

        // Run the generation code
        const result = await pyodide.runPythonAsync(`
import json
from io import BytesIO
from wormgear_geometry import WormParams, WheelParams, AssemblyParams
from wormgear_geometry import WormGeometry, WheelGeometry

# Parse the design JSON
design_data = json.loads(design_json)

# Extract parameters
worm_params = WormParams(**design_data['design']['worm'])
wheel_params = WheelParams(**design_data['design']['wheel'])
assembly_params = AssemblyParams(**design_data['design']['assembly'])

print(f"Generating worm gear pair:")
print(f"  Module: {worm_params.module_mm} mm")
print(f"  Ratio: {assembly_params.ratio}:1")
print(f"  Worm length: {worm_length} mm")
print(f"  Wheel width: {wheel_width or 'auto'} mm")
print(f"  Throated: {throated}")

# Generate worm
print("Generating worm...")
worm_geo = WormGeometry(
    params=worm_params,
    assembly_params=assembly_params,
    length=worm_length,
    sections_per_turn=36
)
worm = worm_geo.build()

# Export worm to bytes
worm_bytes = BytesIO()
worm_geo.export_step(worm_bytes)
worm_step = worm_bytes.getvalue()

print(f"  Worm generated: {len(worm_step)} bytes")

# Generate wheel
print("Generating wheel...")
wheel_geo = WheelGeometry(
    params=wheel_params,
    worm_params=worm_params,
    assembly_params=assembly_params,
    face_width=wheel_width,
    throated=throated
)
wheel = wheel_geo.build()

# Export wheel to bytes
wheel_bytes = BytesIO()
wheel_geo.export_step(wheel_bytes)
wheel_step = wheel_bytes.getvalue()

print(f"  Wheel generated: {len(wheel_step)} bytes")

# Return the STEP files as base64 for transfer to JavaScript
import base64
{
    'worm_step': base64.b64encode(worm_step).decode('utf-8'),
    'wheel_step': base64.b64encode(wheel_step).decode('utf-8'),
    'success': True,
    'message': 'Geometry generated successfully'
}
        `);

        return result.toJs({ dict_converter: Object.fromEntries });

    } catch (error) {
        console.error('Geometry generation failed:', error);
        return {
            success: false,
            message: error.message || 'Unknown error',
            error: error
        };
    }
}

/**
 * Download a file to the user's computer
 * @param {string} filename - Name of the file
 * @param {Blob} blob - File data as Blob
 */
export function downloadFile(filename, blob) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Convert base64 STEP file to downloadable Blob
 * @param {string} base64Data - Base64 encoded STEP file
 * @returns {Blob} - File blob
 */
export function base64ToBlob(base64Data) {
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);

    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    return new Blob([bytes], { type: 'application/step' });
}

/**
 * Test build123d availability and basic functionality
 * @param {object} pyodide - Initialized Pyodide instance
 * @returns {Promise<object>} - Test results
 */
export async function testBuild123d(pyodide) {
    try {
        const result = await pyodide.runPythonAsync(`
import sys

results = {
    'python_version': sys.version,
    'packages': [],
    'build123d_available': False,
    'ocp_available': False,
    'wormgear_available': False
}

# Check installed packages
try:
    import micropip
    packages = await micropip.list()
    results['packages'] = list(packages.keys())
except Exception as e:
    results['packages_error'] = str(e)

# Check build123d
try:
    import build123d
    results['build123d_available'] = True
    results['build123d_version'] = getattr(build123d, '__version__', 'unknown')
except ImportError as e:
    results['build123d_error'] = str(e)

# Check OCP (OpenCascade)
try:
    import OCP
    results['ocp_available'] = True
    results['ocp_version'] = getattr(OCP, '__version__', 'unknown')
except ImportError as e:
    results['ocp_error'] = str(e)

# Check wormgear_geometry
try:
    import wormgear_geometry
    results['wormgear_available'] = True
    results['wormgear_modules'] = dir(wormgear_geometry)
except ImportError as e:
    results['wormgear_error'] = str(e)

results
        `);

        return result.toJs({ dict_converter: Object.fromEntries });

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Install required packages in Pyodide
 * @param {object} pyodide - Initialized Pyodide instance
 * @param {function} progressCallback - Callback for progress updates
 * @returns {Promise<boolean>} - Success status
 */
export async function installDependencies(pyodide, progressCallback = null) {
    const packages = [
        'numpy',
        // Note: build123d and OCP need special handling
        // They may not be available via standard micropip
    ];

    try {
        if (progressCallback) progressCallback('Loading micropip...');

        await pyodide.loadPackage('micropip');
        const micropip = pyodide.pyimport('micropip');

        for (const pkg of packages) {
            if (progressCallback) progressCallback(`Installing ${pkg}...`);
            await micropip.install(pkg);
        }

        if (progressCallback) progressCallback('Dependencies installed');
        return true;

    } catch (error) {
        console.error('Failed to install dependencies:', error);
        if (progressCallback) progressCallback(`Error: ${error.message}`);
        return false;
    }
}
