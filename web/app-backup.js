// Worm Gear Calculator - Browser Application
// Uses Pyodide to run Python calculator in browser

let pyodide = null;
let currentDesign = null;
let currentValidation = null;

// Initialize Pyodide and load wormcalc package
async function initPyodide() {
    try {
        // Show loading screen
        document.getElementById('loading').style.display = 'flex';

        // Load Pyodide
        pyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/"
        });

        // Load local Python files
        const files = ['__init__.py', 'core.py', 'validation.py', 'output.py'];

        // Create directory in Pyodide filesystem
        pyodide.FS.mkdir('/home/pyodide/wormcalc');

        for (const file of files) {
            const response = await fetch(`wormcalc/${file}`);

            if (!response.ok) {
                throw new Error(`Failed to load ${file}: ${response.status} ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && !contentType.includes('text/') && !contentType.includes('application/')) {
                console.warn(`Unexpected content-type for ${file}: ${contentType}`);
            }

            const content = await response.text();

            // Verify content looks like Python
            if (content.trim().startsWith('<!DOCTYPE') || content.trim().startsWith('<html')) {
                throw new Error(`${file} contains HTML instead of Python code. Check your web server configuration.`);
            }

            pyodide.FS.writeFile(`/home/pyodide/wormcalc/${file}`, content);
            console.log(`Loaded ${file} (${content.length} bytes)`);
        }

        // Import module
        await pyodide.runPythonAsync(`
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
        document.getElementById('loading').style.display = 'none';

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
        console.error('Failed to initialize Pyodide:', error);
        document.querySelector('.loading-detail').textContent =
            `Error loading calculator: ${error.message}`;
        document.querySelector('.spinner').style.display = 'none';
    }
}

// Get design function name based on mode
function getDesignFunction(mode) {
    const functions = {
        'envelope': 'design_from_envelope',
        'from-wheel': 'design_from_wheel',
        'from-module': 'design_from_module',
        'from-centre-distance': 'design_from_centre_distance',
    };
    return functions[mode];
}

// Get inputs based on current mode
function getInputs(mode) {
    const pressureAngle = parseFloat(document.getElementById('pressure-angle').value);
    const backlash = parseFloat(document.getElementById('backlash').value);
    const numStarts = parseInt(document.getElementById('num-starts').value);
    const hand = document.getElementById('hand').value;
    const profileShift = parseFloat(document.getElementById('profile-shift').value);
    // Manufacturing options
    const profile = document.getElementById('profile').value;
    const wormType = document.getElementById('worm-type').value;
    const throatReduction = parseFloat(document.getElementById('throat-reduction').value) || 0.0;
    const wheelThroated = document.getElementById('wheel-throated').checked;

    switch (mode) {
        case 'envelope':
            return {
                worm_od: parseFloat(document.getElementById('worm-od').value),
                wheel_od: parseFloat(document.getElementById('wheel-od').value),
                ratio: parseInt(document.getElementById('ratio').value),
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

        case 'from-wheel':
            return {
                wheel_od: parseFloat(document.getElementById('wheel-od-fw').value),
                ratio: parseInt(document.getElementById('ratio-fw').value),
                target_lead_angle: parseFloat(document.getElementById('target-lead-angle').value),
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

        case 'from-module':
            return {
                module: parseFloat(document.getElementById('module').value),
                ratio: parseInt(document.getElementById('ratio-fm').value),
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

        case 'from-centre-distance':
            return {
                centre_distance: parseFloat(document.getElementById('centre-distance').value),
                ratio: parseInt(document.getElementById('ratio-fcd').value),
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

        default:
            return {};
    }
}

// Format arguments for Python function call
function formatArgs(inputs) {
    return Object.entries(inputs)
        .map(([key, value]) => {
            if (key === 'hand') {
                return `hand=Hand.${value}`;
            }
            if (key === 'profile') {
                return `profile=WormProfile.${value}`;
            }
            if (key === 'worm_type') {
                return `worm_type=WormType.${value.toUpperCase()}`;
            }
            if (key === 'wheel_throated') {
                return `wheel_throated=${value ? 'True' : 'False'}`;
            }
            if (key === 'throat_reduction') {
                return `throat_reduction=${value}`;
            }
            return `${key}=${value}`;
        })
        .join(', ');
}

// Main calculation function
function calculate() {
    if (!pyodide) {
        console.log('Pyodide not ready yet');
        return;
    }

    try {
        const mode = document.getElementById('mode').value;
        const inputs = getInputs(mode);
        const func = getDesignFunction(mode);
        const args = formatArgs(inputs);
        const useStandardModule = document.getElementById('use-standard-module').checked;
        const odAsMaximum = mode === 'envelope' ? document.getElementById('od-as-maximum').checked : false;

        console.log(`Calling ${func}(${args})`);

        // Run Python calculation
        const result = pyodide.runPython(`
import json

# Initial design calculation
design = ${func}(${args})

# Check if we should round to standard module
use_standard = ${useStandardModule ? 'True' : 'False'}
od_as_maximum = ${odAsMaximum ? 'True' : 'False'}
mode = "${mode}"
adjusted_module = None

if use_standard and mode != "from-module":
    # Get calculated module and find nearest standard
    calculated_module = design.worm.module
    standard_module = nearest_standard_module(calculated_module)

    # Special handling for envelope mode with OD as maximum
    if mode == "envelope" and od_as_maximum:
        from wormcalc.core import STANDARD_MODULES

        # User's specified maximum ODs
        user_worm_od = ${inputs.worm_od || 20}
        user_wheel_od = ${inputs.wheel_od || 65}

        # Try standard modules in descending order to find largest that fits
        # Start from the original envelope design's worm pitch diameter to maximize size
        found_module = None
        base_worm_pitch_diameter = design.worm.pitch_diameter

        for test_module in sorted(STANDARD_MODULES, reverse=True):
            try:
                # Preserve worm pitch diameter from original envelope design,
                # adjusting for different module addendum
                addendum_change = test_module - calculated_module
                test_worm_pitch_diameter = base_worm_pitch_diameter - 2 * addendum_change

                # Skip if adjusted pitch diameter is too small
                if test_worm_pitch_diameter <= 0:
                    continue

                test_design = design_from_module(
                    module=test_module,
                    ratio=${inputs.ratio || 30},
                    worm_pitch_diameter=test_worm_pitch_diameter,
                    pressure_angle=${inputs.pressure_angle || 20},
                    backlash=${inputs.backlash || 0},
                    num_starts=${inputs.num_starts || 1},
                    hand=Hand.${inputs.hand || 'RIGHT'},
                    profile_shift=${inputs.profile_shift || 0},
                    profile=WormProfile.${inputs.profile || 'ZA'},
                    worm_type=WormType.${(inputs.worm_type || 'cylindrical').toUpperCase()},
                    throat_reduction=${inputs.throat_reduction || 0.0},
                    wheel_throated=${inputs.wheel_throated ? 'True' : 'False'}
                )

                # Check if both ODs fit within maximums
                if test_design.worm.tip_diameter <= user_worm_od and test_design.wheel.tip_diameter <= user_wheel_od:
                    found_module = test_module
                    standard_module = test_module
                    design = test_design
                    break
            except (ZeroDivisionError, ValueError):
                # This module doesn't work, skip to next
                continue

        # If we found a module that fits, update adjusted_module info
        if found_module and abs(calculated_module - standard_module) > 0.001:
            adjusted_module = {
                'calculated': calculated_module,
                'standard': standard_module
            }
        elif not found_module:
            # No standard module fits within OD constraints, use nearest anyway
            standard_module = nearest_standard_module(calculated_module)
            if abs(calculated_module - standard_module) > 0.001:
                adjusted_module = {
                    'calculated': calculated_module,
                    'standard': standard_module
                }
                # Calculate with nearest module even though it exceeds ODs
                worm_pitch_diameter = design.worm.pitch_diameter
                addendum_change = standard_module - calculated_module
                worm_pitch_diameter = worm_pitch_diameter - 2 * addendum_change

                design = design_from_module(
                    module=standard_module,
                    ratio=${inputs.ratio || 30},
                    worm_pitch_diameter=worm_pitch_diameter,
                    pressure_angle=${inputs.pressure_angle || 20},
                    backlash=${inputs.backlash || 0},
                    num_starts=${inputs.num_starts || 1},
                    hand=Hand.${inputs.hand || 'RIGHT'},
                    profile_shift=${inputs.profile_shift || 0},
                    profile=WormProfile.${inputs.profile || 'ZA'},
                    worm_type=WormType.${(inputs.worm_type || 'cylindrical').toUpperCase()},
                    throat_reduction=${inputs.throat_reduction || 0.0},
                    wheel_throated=${inputs.wheel_throated ? 'True' : 'False'}
                )
    # If different, recalculate using standard module
    elif abs(calculated_module - standard_module) > 0.001:
        adjusted_module = {
            'calculated': calculated_module,
            'standard': standard_module
        }

        # FIXED: Preserve worm OD constraint when rounding from envelope mode
        if mode == "envelope":
            # Calculate worm_pitch_diameter to preserve approximate OD
            worm_pitch_diameter = design.worm.pitch_diameter
            # Adjust for module change to maintain similar OD
            # OD = pitch + 2*addendum, so adjust pitch to compensate for addendum change
            addendum_change = standard_module - calculated_module
            worm_pitch_diameter = worm_pitch_diameter - 2 * addendum_change

            design = design_from_module(
                module=standard_module,
                ratio=${inputs.ratio || 30},
                worm_pitch_diameter=worm_pitch_diameter,
                pressure_angle=${inputs.pressure_angle || 20},
                backlash=${inputs.backlash || 0},
                num_starts=${inputs.num_starts || 1},
                hand=Hand.${inputs.hand || 'RIGHT'},
                profile_shift=${inputs.profile_shift || 0},
                profile=WormProfile.${inputs.profile || 'ZA'},
                worm_type=WormType.${(inputs.worm_type || 'cylindrical').toUpperCase()},
                throat_reduction=${inputs.throat_reduction || 0.0},
                wheel_throated=${inputs.wheel_throated ? 'True' : 'False'}
            )
        else:
            # For non-envelope modes, use target lead angle as before
            design = design_from_module(
                module=standard_module,
                ratio=${inputs.ratio || 30},
                pressure_angle=${inputs.pressure_angle || 20},
                backlash=${inputs.backlash || 0},
                num_starts=${inputs.num_starts || 1},
                hand=Hand.${inputs.hand || 'RIGHT'},
                profile_shift=${inputs.profile_shift || 0},
                profile=WormProfile.${inputs.profile || 'ZA'},
                worm_type=WormType.${(inputs.worm_type || 'cylindrical').toUpperCase()},
                throat_reduction=${inputs.throat_reduction || 0.0},
                wheel_throated=${inputs.wheel_throated ? 'True' : 'False'}
            )

validation = validate_design(design)

# Store globally for export functions
globals()['current_design'] = design
globals()['current_validation'] = validation

json.dumps({
    'summary': to_summary(design),
    'json_output': to_json(design, validation),
    'markdown': to_markdown(design, validation),
    'valid': validation.valid,
    'module': design.worm.module,
    'adjusted_module': adjusted_module,
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

        // Store for export
        currentDesign = data.json_output;

        updateUI(data);

    } catch (error) {
        console.error('Calculation error:', error);
        document.getElementById('validation-status').textContent = `Error: ${error.message}`;
        document.getElementById('validation-status').className = 'status-error';
    }
}

// Update UI with calculation results
function updateUI(data) {
    // Update results
    document.getElementById('results-text').textContent = data.summary;

    // Update validation status
    const statusEl = document.getElementById('validation-status');
    if (data.valid) {
        statusEl.textContent = '✓ Design valid';
        statusEl.className = 'status-valid';
    } else {
        statusEl.textContent = '✗ Design has errors';
        statusEl.className = 'status-invalid';
    }

    // Update module info if adjusted
    const moduleInfoEl = document.getElementById('module-info');
    if (data.adjusted_module) {
        moduleInfoEl.style.display = 'block';
        moduleInfoEl.innerHTML = `ℹ Module adjusted: ${data.adjusted_module.calculated.toFixed(3)} mm → <strong>${data.adjusted_module.standard} mm</strong> (ISO 54 standard)`;
    } else if (data.module) {
        const useStandard = document.getElementById('use-standard-module').checked;
        const mode = document.getElementById('mode').value;
        if (mode === 'from-module' || !useStandard) {
            moduleInfoEl.style.display = 'block';
            moduleInfoEl.innerHTML = `ℹ Module: <strong>${data.module} mm</strong>`;
        } else {
            moduleInfoEl.style.display = 'none';
        }
    } else {
        moduleInfoEl.style.display = 'none';
    }

    // Update validation messages
    const messagesEl = document.getElementById('validation-messages');
    messagesEl.innerHTML = '';

    data.messages.forEach(msg => {
        const li = document.createElement('li');
        li.className = `message-${msg.severity}`;

        const icon = msg.severity === 'error' ? '✗' :
                     msg.severity === 'warning' ? '⚠' : 'ℹ';

        // Create message text with suggestion if available
        let messageText = `${icon} ${msg.message}`;
        if (msg.suggestion) {
            messageText += `\n    → ${msg.suggestion}`;
        }

        li.textContent = messageText;
        li.style.whiteSpace = 'pre-line';  // Preserve line breaks
        messagesEl.appendChild(li);
    });

    // Store markdown for download
    window.currentMarkdown = data.markdown;
}

// Mode change handler
function onModeChange() {
    const mode = document.getElementById('mode').value;

    // Hide all mode input groups
    document.querySelectorAll('#mode-inputs .input-group').forEach(group => {
        group.style.display = 'none';
    });

    // Show selected mode inputs
    const selectedGroup = document.querySelector(`#mode-inputs .input-group[data-mode="${mode}"]`);
    if (selectedGroup) {
        selectedGroup.style.display = 'block';
    }

    // Recalculate
    calculate();
}

// Debounced input handler
let debounceTimer;
function onInputChange() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(calculate, 300);
}

// Export: Copy JSON to clipboard
function copyJson() {
    if (currentDesign) {
        navigator.clipboard.writeText(currentDesign)
            .then(() => {
                showNotification('JSON copied to clipboard!');
            })
            .catch(err => {
                console.error('Failed to copy:', err);
                showNotification('Failed to copy JSON', true);
            });
    }
}

// Export: Download JSON
function downloadJson() {
    if (currentDesign) {
        const blob = new Blob([currentDesign], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'worm-gear-design.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification('JSON file downloaded!');
    }
}

// Export: Download Markdown
function downloadMarkdown() {
    if (window.currentMarkdown) {
        const blob = new Blob([window.currentMarkdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'worm-gear-design.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification('Markdown file downloaded!');
    }
}

// Export: Copy share link
function copyShareLink() {
    const mode = document.getElementById('mode').value;
    const inputs = getInputs(mode);

    const params = new URLSearchParams();
    params.set('mode', mode);

    // Add mode-specific inputs
    Object.entries(inputs).forEach(([key, value]) => {
        params.set(key, value);
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

// Load inputs from URL parameters
function loadFromUrl() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('mode')) {
        const mode = params.get('mode');
        document.getElementById('mode').value = mode;
        onModeChange();

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

// Show/hide throat reduction input based on worm type
function onWormTypeChange() {
    const wormType = document.getElementById('worm-type').value;
    const throatGroup = document.getElementById('throat-reduction-group');

    if (wormType === 'globoid') {
        throatGroup.style.display = 'block';
    } else {
        throatGroup.style.display = 'none';
    }

    // Recalculate
    onInputChange();
}

// Set up event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Mode selector
    document.getElementById('mode').addEventListener('change', onModeChange);

    // Worm type selector - show/hide throat reduction
    document.getElementById('worm-type').addEventListener('change', onWormTypeChange);

    // All inputs with debounce
    document.querySelectorAll('input, select').forEach(el => {
        if (el.id !== 'mode' && el.id !== 'worm-type') {
            el.addEventListener('input', onInputChange);
        }
    });

    // Checkboxes need 'change' event for immediate response
    document.getElementById('use-standard-module').addEventListener('change', calculate);
    document.getElementById('wheel-throated').addEventListener('change', calculate);
    document.getElementById('od-as-maximum').addEventListener('change', calculate);

    // Export buttons
    document.getElementById('copy-json').addEventListener('click', copyJson);
    document.getElementById('download-json').addEventListener('click', downloadJson);
    document.getElementById('download-md').addEventListener('click', downloadMarkdown);
    document.getElementById('copy-link').addEventListener('click', copyShareLink);

    // Initialize Pyodide
    initPyodide();
});
