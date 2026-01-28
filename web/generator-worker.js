// generator-worker.js
// Web Worker for wormgear geometry generation
// Runs Pyodide + build123d + OCP in background thread to keep UI responsive

let pyodide = null;
let isLoading = false;
let loadComplete = false;

// Listen for messages from main thread
self.onmessage = async (e) => {
    const { type, data } = e.data;

    if (type === 'INIT') {
        await initializePyodide();
    } else if (type === 'GENERATE') {
        await generateGeometry(data);
    }
};

async function initializePyodide() {
    if (loadComplete) {
        self.postMessage({ type: 'INIT_COMPLETE' });
        return;
    }

    if (isLoading) {
        self.postMessage({ type: 'INIT_ERROR', error: 'Already loading' });
        return;
    }

    isLoading = true;

    try {
        self.postMessage({ type: 'LOG', message: 'Loading Pyodide...' });

        // Load Pyodide
        self.importScripts('https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js');

        pyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.0/full/",
            stdout: (text) => {
                if (text.trim()) self.postMessage({ type: 'LOG', message: `[py] ${text}` });
            },
            stderr: (text) => {
                if (text.trim()) self.postMessage({ type: 'LOG', message: `[py:err] ${text}` });
            }
        });

        self.postMessage({ type: 'LOG', message: '✓ Pyodide loaded' });

        // Install micropip and pydantic (pydantic must use loadPackage, not micropip, due to pydantic-core)
        self.postMessage({ type: 'LOG', message: 'Installing micropip and pydantic...' });
        await pyodide.loadPackage(['micropip', 'pydantic']);
        const micropip = pyodide.pyimport('micropip');
        self.postMessage({ type: 'LOG', message: '✓ micropip and pydantic ready' });

        // Install build123d and OCP
        self.postMessage({ type: 'LOG', message: '📦 Installing build123d and OCP (2-5 minutes)...' });
        self.postMessage({ type: 'LOG', message: '⏳ Large download - please be patient...' });

        const result = await pyodide.runPythonAsync(`
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
            self.postMessage({ type: 'LOG', message: '✓ All packages installed!' });

            // Load wormgear package
            await loadWormGearPackage();

            loadComplete = true;
            self.postMessage({ type: 'INIT_COMPLETE' });
            self.postMessage({ type: 'LOG', message: 'Generator ready!' });
        } else {
            throw new Error('Package installation failed');
        }

    } catch (error) {
        // Better error handling - ensure we always get a string
        const errorMessage = error?.message || error?.toString() || String(error) || 'Unknown initialization error';
        const errorStack = error?.stack || '';

        console.error('[Worker] Init error:', error);

        self.postMessage({
            type: 'INIT_ERROR',
            error: errorMessage,
            stack: errorStack
        });
    } finally {
        isLoading = false;
    }
}

async function loadWormGearPackage() {
    self.postMessage({ type: 'LOG', message: 'Loading wormgear package...' });

    // Create package directory structure
    await pyodide.runPythonAsync(`
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

    // Define files to load
    const packageFiles = [
        { path: 'wormgear/__init__.py', pyPath: '/home/pyodide/wormgear/__init__.py' },
        { path: 'wormgear/enums.py', pyPath: '/home/pyodide/wormgear/enums.py' },
        { path: 'wormgear/core/__init__.py', pyPath: '/home/pyodide/wormgear/core/__init__.py' },
        { path: 'wormgear/core/worm.py', pyPath: '/home/pyodide/wormgear/core/worm.py' },
        { path: 'wormgear/core/wheel.py', pyPath: '/home/pyodide/wormgear/core/wheel.py' },
        { path: 'wormgear/core/features.py', pyPath: '/home/pyodide/wormgear/core/features.py' },
        { path: 'wormgear/core/globoid_worm.py', pyPath: '/home/pyodide/wormgear/core/globoid_worm.py' },
        { path: 'wormgear/core/virtual_hobbing.py', pyPath: '/home/pyodide/wormgear/core/virtual_hobbing.py' },
        { path: 'wormgear/core/bore_sizing.py', pyPath: '/home/pyodide/wormgear/core/bore_sizing.py' },
        { path: 'wormgear/io/__init__.py', pyPath: '/home/pyodide/wormgear/io/__init__.py' },
        { path: 'wormgear/io/loaders.py', pyPath: '/home/pyodide/wormgear/io/loaders.py' },
        { path: 'wormgear/io/schema.py', pyPath: '/home/pyodide/wormgear/io/schema.py' },
        { path: 'wormgear/calculator/__init__.py', pyPath: '/home/pyodide/wormgear/calculator/__init__.py' },
        { path: 'wormgear/calculator/core.py', pyPath: '/home/pyodide/wormgear/calculator/core.py' },
        { path: 'wormgear/calculator/validation.py', pyPath: '/home/pyodide/wormgear/calculator/validation.py' },
        { path: 'wormgear/calculator/output.py', pyPath: '/home/pyodide/wormgear/calculator/output.py' },
        { path: 'wormgear/calculator/constants.py', pyPath: '/home/pyodide/wormgear/calculator/constants.py' },
        { path: 'wormgear/calculator/js_bridge.py', pyPath: '/home/pyodide/wormgear/calculator/js_bridge.py' },
        { path: 'wormgear/calculator/json_schema.py', pyPath: '/home/pyodide/wormgear/calculator/json_schema.py' },
    ];

    // Load all files
    for (const file of packageFiles) {
        const response = await fetch(file.path);  // Removed 'src/' prefix - wormgear is at root of dist/
        if (!response.ok) {
            throw new Error('Failed to fetch ' + file.path + ': ' + response.status);
        }
        const content = await response.text();
        pyodide.FS.writeFile(file.pyPath, content);
    }

    self.postMessage({ type: 'LOG', message: `✓ Loaded ${packageFiles.length} package files` });

    // Test import
    await pyodide.runPythonAsync(`
import wormgear
from wormgear.core import WormGeometry, WheelGeometry
from wormgear.io import WormParams, WheelParams, AssemblyParams
print(f"✓ wormgear package loaded (version {wormgear.__version__})")
    `);

    self.postMessage({ type: 'LOG', message: '✓ wormgear package ready' });
}

async function generateGeometry(data) {
    if (!loadComplete) {
        self.postMessage({
            type: 'GENERATE_ERROR',
            error: 'Pyodide not loaded. Initialize first.'
        });
        return;
    }

    try {
        const {
            designData,
            wormLength,
            wheelWidth,
            virtualHobbing,
            hobbingSteps,
            generateType
        } = data;

        self.postMessage({ type: 'LOG', message: '⏳ Starting geometry generation...' });

        // Create JavaScript function accessible to Python
        self.postProgressUpdate = (message, percent) => {
            console.log('[Worker] Progress update:', message, percent);
            self.postMessage({
                type: 'PROGRESS',
                message: message,
                percent: percent
            });
        };

        // Create progress callback that posts messages to main thread
        const progressCallback = pyodide.runPython(`
def progress_callback(message, percent):
    """Progress callback - sends updates to main thread via worker"""
    import js
    print(f"[Python] Progress: {message} ({percent}%)")
    js.postProgressUpdate(message, percent)

progress_callback
        `);

        // Set Python globals
        pyodide.globals.set('design_json_str', JSON.stringify(designData));
        pyodide.globals.set('worm_length', wormLength);
        pyodide.globals.set('wheel_width_val', wheelWidth || null);
        pyodide.globals.set('virtual_hobbing_val', virtualHobbing);
        pyodide.globals.set('hobbing_steps_val', hobbingSteps);
        pyodide.globals.set('generate_type', generateType);
        pyodide.globals.set('progress_callback_fn', progressCallback);

        // Run generation
        const result = await pyodide.runPythonAsync(`
import json
import base64
import tempfile
import os
import logging

# Configure logging - INFO for wormgear modules, suppress verbose build123d internals
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(levelname)s: %(message)s')
for logger_name in ['wormgear.core.worm', 'wormgear.core.wheel', 'wormgear.core.globoid_worm', 'wormgear.core.virtual_hobbing', 'wormgear.core.features']:
    logging.getLogger(logger_name).setLevel(logging.INFO)
# Suppress build123d's verbose internal logging (BuildSketch, WorkplaneList, etc.)
logging.getLogger('build123d').setLevel(logging.WARNING)

from wormgear.core import WormGeometry, WheelGeometry, GloboidWormGeometry, VirtualHobbingWheelGeometry, BoreFeature, KeywayFeature, DDCutFeature, calculate_default_bore
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

# Parse features section for bores and keyways
features = design_data.get('features', {}) or {}  # Handle None case

# Worm features
worm_bore = None
worm_keyway = None
worm_ddcut = None
worm_bore_diameter = None

if 'worm' in features:
    worm_feat = features['worm']
    if 'bore_diameter_mm' in worm_feat and worm_feat['bore_diameter_mm'] is not None:
        worm_bore_diameter = worm_feat['bore_diameter_mm']
        print(f"Worm bore: {worm_bore_diameter} mm")

    # Create bore feature if diameter was determined
    if worm_bore_diameter is not None:
        worm_bore = BoreFeature(diameter=worm_bore_diameter)

        # Add anti-rotation feature if specified (keyway and ddcut are mutually exclusive)
        if 'anti_rotation' in worm_feat:
            anti_rot = worm_feat['anti_rotation']

            if anti_rot == 'DIN6885':
                if worm_bore_diameter >= 6.0:
                    print(f"Worm keyway: DIN 6885")
                    worm_keyway = KeywayFeature()
                else:
                    print(f"Worm keyway: skipped (bore {worm_bore_diameter}mm < 6mm minimum for DIN 6885)")

            elif anti_rot == 'ddcut':
                # Calculate depth as ~10% of bore diameter (standard practice for small shafts)
                dd_depth = round(worm_bore_diameter * 0.1, 1)
                print(f"Worm DD-cut: double-D flat anti-rotation (depth={dd_depth}mm)")
                worm_ddcut = DDCutFeature(depth=dd_depth)

            elif anti_rot not in ['none', '']:
                print(f"Worm anti-rotation: unknown type '{anti_rot}', skipping")

# Wheel features
wheel_bore = None
wheel_keyway = None
wheel_ddcut = None
wheel_bore_diameter = None

if 'wheel' in features:
    wheel_feat = features['wheel']
    if 'bore_diameter_mm' in wheel_feat and wheel_feat['bore_diameter_mm'] is not None:
        wheel_bore_diameter = wheel_feat['bore_diameter_mm']
        print(f"Wheel bore: {wheel_bore_diameter} mm")

    # Create bore feature if diameter was determined
    if wheel_bore_diameter is not None:
        wheel_bore = BoreFeature(diameter=wheel_bore_diameter)

        # Add anti-rotation feature if specified (keyway and ddcut are mutually exclusive)
        if 'anti_rotation' in wheel_feat:
            anti_rot = wheel_feat['anti_rotation']

            if anti_rot == 'DIN6885':
                if wheel_bore_diameter >= 6.0:
                    print(f"Wheel keyway: DIN 6885")
                    wheel_keyway = KeywayFeature()
                else:
                    print(f"Wheel keyway: skipped (bore {wheel_bore_diameter}mm < 6mm minimum for DIN 6885)")

            elif anti_rot == 'ddcut':
                # Calculate depth as ~10% of bore diameter (standard practice for small shafts)
                dd_depth = round(wheel_bore_diameter * 0.1, 1)
                print(f"Wheel DD-cut: double-D flat anti-rotation (depth={dd_depth}mm)")
                wheel_ddcut = DDCutFeature(depth=dd_depth)

            elif anti_rot not in ['none', '']:
                print(f"Wheel anti-rotation: unknown type '{anti_rot}', skipping")

print("✓ Parameters parsed")
print("")

worm_b64 = None
wheel_b64 = None
worm_3mf_b64 = None
wheel_3mf_b64 = None
worm_stl_b64 = None
wheel_stl_b64 = None
worm = None  # Will hold worm geometry if generated

# Check if globoid - either by type field or presence of throat curvature radius
# Note: worm_params.type is a WormType enum, so compare .value or check throat_curvature_radius_mm
worm_type_value = getattr(worm_params.type, 'value', worm_params.type) if hasattr(worm_params, 'type') and worm_params.type else None
is_globoid = (worm_type_value == 'globoid') or \
             (hasattr(worm_params, 'throat_curvature_radius_mm') and worm_params.throat_curvature_radius_mm is not None)
print(f"Worm type: {worm_type_value}, is_globoid: {is_globoid}")

# Generate worm if requested
if generate_type in ['worm', 'both']:
    print("🔩 Generating worm gear...")
    try:
        print("  Creating worm geometry object...")
        if is_globoid:
            print("  Using globoid (hourglass) worm geometry...")
            worm_geo = GloboidWormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                wheel_pitch_diameter=wheel_params.pitch_diameter_mm,
                length=worm_length,
                sections_per_turn=36,
                bore=worm_bore,
                keyway=worm_keyway,
                ddcut=worm_ddcut
            )
        else:
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=worm_length,
                sections_per_turn=36,
                bore=worm_bore,
                keyway=worm_keyway,
                ddcut=worm_ddcut
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

        # Export 3MF for 3D printing (preferred - has explicit units and better precision)
        # Note: 3MF export can fail for complex geometry due to mesh issues - make it non-fatal
        try:
            print("  Exporting to 3MF format...")

            # Validate shape before meshing (diagnostic)
            shape_valid = worm.is_valid
            print(f"    Shape validity check: {shape_valid}")
            if not shape_valid:
                print("    ⚠️ Shape has validity issues - 3MF may fail")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.3mf', delete=False) as tmp:
                temp_3mf_path = tmp.name

            # Use build123d Mesher for 3MF export with finer mesh settings
            # Lower deflection values = finer mesh, may help avoid duplicate vertex issues
            from build123d import Mesher, Unit
            mesher = Mesher(unit=Unit.MM)
            mesher.add_shape(
                worm,
                linear_deflection=0.0005,   # Finer than default 0.001
                angular_deflection=0.05     # Finer than default 0.1
            )
            mesher.write(temp_3mf_path)

            # Read back as bytes
            with open(temp_3mf_path, 'rb') as f:
                worm_3mf = f.read()

            # Clean up temp file
            os.unlink(temp_3mf_path)

            worm_3mf_b64 = base64.b64encode(worm_3mf).decode('utf-8')
        except Exception as e:
            print(f"  ⚠️ 3MF export failed (non-fatal): {e}")
            print(f"    This is a known issue with complex geometry meshing.")
            print(f"    STEP and STL files are still available.")
            worm_3mf_b64 = None

        # Also export STL for compatibility
        # Use finer mesh settings consistent with 3MF export for better detail
        print("  Exporting to STL format...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as tmp:
            temp_stl_path = tmp.name

        from build123d import export_stl
        export_stl(
            worm,
            temp_stl_path,
            tolerance=0.0005,       # Finer than default 0.001 for better gear tooth detail
            angular_tolerance=0.05  # Finer than default 0.1 for curved surfaces
        )

        with open(temp_stl_path, 'rb') as f:
            worm_stl = f.read()

        os.unlink(temp_stl_path)
        worm_stl_b64 = base64.b64encode(worm_stl).decode('utf-8')

        size_kb = len(worm_step) / 1024
        mf3_size_kb = len(worm_3mf) / 1024 if worm_3mf_b64 else 0
        stl_size_kb = len(worm_stl) / 1024
        print(f"✓ Worm generated successfully!")
        mf3_status = f"{mf3_size_kb:.1f} KB" if worm_3mf_b64 else "failed"
        print(f"  STEP: {size_kb:.1f} KB, 3MF: {mf3_status}, STL: {stl_size_kb:.1f} KB")
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
        # Debug: Log virtual hobbing settings
        print(f"  [DEBUG] virtual_hobbing_val = {virtual_hobbing_val} (type: {type(virtual_hobbing_val).__name__})")
        print(f"  [DEBUG] hobbing_steps_val = {hobbing_steps_val}")

        # Use VirtualHobbingWheelGeometry if virtual_hobbing enabled, otherwise regular WheelGeometry
        if virtual_hobbing_val:
            # Virtual hobbing supports progress callbacks
            print(f"  Using virtual hobbing with {hobbing_steps_val} steps...")

            # Pass the actual worm geometry as hob ONLY for globoid (important for accuracy)
            # For cylindrical, let VirtualHobbingWheelGeometry create a simpler hob internally
            hob_geo = worm if (generate_type == 'both' and is_globoid) else None
            hob_type = "globoid" if is_globoid else "cylindrical"
            print(f"  Using {hob_type} hob geometry")

            wheel_geo = VirtualHobbingWheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=wheel_width,
                hobbing_steps=hobbing_steps_val,
                progress_callback=progress_callback_fn,
                bore=wheel_bore,
                keyway=wheel_keyway,
                ddcut=wheel_ddcut,
                hob_geometry=hob_geo
            )
        else:
            # Regular helical wheel (no progress callbacks needed - it's fast)
            wheel_geo = WheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=wheel_width,
                bore=wheel_bore,
                keyway=wheel_keyway,
                ddcut=wheel_ddcut
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

        # Export 3MF for 3D printing (preferred - has explicit units and better precision)
        # Note: 3MF export can fail for complex geometry due to mesh issues - make it non-fatal
        try:
            print("  Exporting to 3MF format...")

            # Validate shape before meshing (diagnostic)
            shape_valid = wheel.is_valid
            print(f"    Shape validity check: {shape_valid}")
            if not shape_valid:
                print("    ⚠️ Shape has validity issues - 3MF may fail")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.3mf', delete=False) as tmp:
                temp_3mf_path = tmp.name

            # Use build123d Mesher for 3MF export with finer mesh settings
            # Lower deflection values = finer mesh, may help avoid duplicate vertex issues
            from build123d import Mesher, Unit
            mesher = Mesher(unit=Unit.MM)
            mesher.add_shape(
                wheel,
                linear_deflection=0.0005,   # Finer than default 0.001
                angular_deflection=0.05     # Finer than default 0.1
            )
            mesher.write(temp_3mf_path)

            # Read back as bytes
            with open(temp_3mf_path, 'rb') as f:
                wheel_3mf = f.read()

            # Clean up temp file
            os.unlink(temp_3mf_path)

            wheel_3mf_b64 = base64.b64encode(wheel_3mf).decode('utf-8')
        except Exception as e:
            print(f"  ⚠️ 3MF export failed (non-fatal): {e}")
            print(f"    This is a known issue with complex geometry meshing.")
            print(f"    STEP and STL files are still available.")
            wheel_3mf_b64 = None

        # Also export STL for compatibility
        # Use finer mesh settings consistent with 3MF export for better detail
        print("  Exporting to STL format...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as tmp:
            temp_stl_path = tmp.name

        from build123d import export_stl
        export_stl(
            wheel,
            temp_stl_path,
            tolerance=0.0005,       # Finer than default 0.001 for better gear tooth detail
            angular_tolerance=0.05  # Finer than default 0.1 for curved surfaces
        )

        with open(temp_stl_path, 'rb') as f:
            wheel_stl = f.read()

        os.unlink(temp_stl_path)
        wheel_stl_b64 = base64.b64encode(wheel_stl).decode('utf-8')

        size_kb = len(wheel_step) / 1024
        mf3_size_kb = len(wheel_3mf) / 1024 if wheel_3mf_b64 else 0
        stl_size_kb = len(wheel_stl) / 1024
        print(f"✓ Wheel generated successfully!")
        mf3_status = f"{mf3_size_kb:.1f} KB" if wheel_3mf_b64 else "failed"
        print(f"  STEP: {size_kb:.1f} KB, 3MF: {mf3_status}, STL: {stl_size_kb:.1f} KB")
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

# Return results (markdown will be generated on main thread using calculator Pyodide)
{
    'worm': worm_b64,
    'wheel': wheel_b64,
    'worm_3mf': worm_3mf_b64,
    'wheel_3mf': wheel_3mf_b64,
    'worm_stl': worm_stl_b64,
    'wheel_stl': wheel_stl_b64,
    'success': (generate_type == 'worm' and worm_b64 is not None) or
               (generate_type == 'wheel' and wheel_b64 is not None) or
               (generate_type == 'both' and worm_b64 is not None and wheel_b64 is not None)
}
        `);

        // Send results back to main thread
        const success = result.get('success');
        const wormB64 = result.get('worm');
        const wheelB64 = result.get('wheel');
        const worm3mfB64 = result.get('worm_3mf');
        const wheel3mfB64 = result.get('wheel_3mf');
        const wormStlB64 = result.get('worm_stl');
        const wheelStlB64 = result.get('wheel_stl');

        self.postMessage({
            type: 'GENERATE_COMPLETE',
            success: success,
            worm: wormB64,
            wheel: wheelB64,
            worm_3mf: worm3mfB64,
            wheel_3mf: wheel3mfB64,
            worm_stl: wormStlB64,
            wheel_stl: wheelStlB64
        });

    } catch (error) {
        // Better error handling - ensure we always get a string
        const errorMessage = error?.message || error?.toString() || String(error) || 'Unknown error';
        const errorStack = error?.stack || '';

        console.error('[Worker] Generate error:', error);

        self.postMessage({
            type: 'GENERATE_ERROR',
            error: errorMessage,
            stack: errorStack
        });
    }
}
