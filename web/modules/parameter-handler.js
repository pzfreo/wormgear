/**
 * Parameter Handler Module
 *
 * Collects parameters from UI and prepares them for the Python calculator.
 * Works with schema-validator.js for runtime type checking.
 */

import { validateCalculatorInputs } from './schema-validator.js';

/**
 * Safely parse a float value
 * @param {string} value
 * @returns {number|null}
 */
function safeParseFloat(value) {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? null : parsed;
}

/**
 * Safely parse an integer value
 * @param {string} value
 * @returns {number|null}
 */
function safeParseInt(value) {
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? null : parsed;
}

/**
 * Get element value safely
 * @param {string} id
 * @returns {string}
 */
function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

/**
 * Get checkbox state safely
 * @param {string} id
 * @returns {boolean}
 */
function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

/**
 * Collect all inputs from UI into a structured object.
 * Returns data in the format expected by the Python js_bridge.calculate() function.
 *
 * @param {string} mode - Calculation mode
 * @returns {object} Validated inputs ready for JSON serialization
 */
export function getInputs(mode) {
    // Collect bore settings
    const bore = {
        worm_bore_type: getValue('worm-bore-type'),
        worm_bore_diameter: safeParseFloat(getValue('worm-bore-diameter')),
        worm_keyway: getValue('worm-anti-rotation'),
        wheel_bore_type: getValue('wheel-bore-type'),
        wheel_bore_diameter: safeParseFloat(getValue('wheel-bore-diameter')),
        wheel_keyway: getValue('wheel-anti-rotation')
    };

    // Collect manufacturing settings
    const wheelGeneration = getValue('wheel-generation');
    const hobbingPrecision = getValue('hobbing-precision');
    const hobbingStepsMap = {
        'preview': 36,
        'balanced': 72,
        'high': 144
    };

    const manufacturing = {
        virtual_hobbing: wheelGeneration === 'virtual-hobbing',
        hobbing_steps: hobbingStepsMap[hobbingPrecision] || 72,
        use_recommended_dims: getChecked('use-recommended-dims'),
        worm_length: safeParseFloat(getValue('worm-length')),
        wheel_width: safeParseFloat(getValue('wheel-width'))
    };

    // Build raw inputs object
    const rawInputs = {
        mode: mode,
        pressure_angle: safeParseFloat(getValue('pressure-angle')),
        backlash: safeParseFloat(getValue('backlash')),
        num_starts: safeParseInt(getValue('num-starts')),
        hand: getValue('hand'),
        profile_shift: safeParseFloat(getValue('profile-shift')) || 0,
        profile: getValue('profile'),
        worm_type: getValue('worm-type'),
        throat_reduction: safeParseFloat(getValue('throat-reduction')) || 0,
        wheel_throated: getChecked('wheel-throated'),
        bore: bore,
        manufacturing: manufacturing
    };

    // Add mode-specific parameters
    switch (mode) {
        case 'envelope':
            rawInputs.worm_od = safeParseFloat(getValue('worm-od'));
            rawInputs.wheel_od = safeParseFloat(getValue('wheel-od'));
            rawInputs.ratio = safeParseInt(getValue('ratio'));
            rawInputs.od_as_maximum = getChecked('od-as-maximum');
            rawInputs.use_standard_module = getChecked('use-standard-module');
            break;
        case 'from-wheel':
            rawInputs.wheel_od = safeParseFloat(getValue('wheel-od-fw'));
            rawInputs.ratio = safeParseInt(getValue('ratio-fw'));
            rawInputs.target_lead_angle = safeParseFloat(getValue('target-lead-angle'));
            break;
        case 'from-module':
            rawInputs.module = safeParseFloat(getValue('module'));
            rawInputs.ratio = safeParseInt(getValue('ratio-fm'));
            break;
        case 'from-centre-distance':
            rawInputs.centre_distance = safeParseFloat(getValue('centre-distance'));
            rawInputs.ratio = safeParseInt(getValue('ratio-fcd'));
            break;
    }

    // Validate and return
    return validateCalculatorInputs(rawInputs);
}

/**
 * Get the Python function name for the design mode.
 * @deprecated Use the new js_bridge.calculate() which handles mode internally
 * @param {string} mode
 * @returns {string}
 */
export function getDesignFunction(mode) {
    const functions = {
        'envelope': 'design_from_envelope',
        'from-wheel': 'design_from_wheel',
        'from-module': 'design_from_module',
        'from-centre-distance': 'design_from_centre_distance',
    };
    return functions[mode];
}

/**
 * Format calculator parameters for Python function call.
 * @deprecated Use the new js_bridge.calculate() which handles formatting internally
 * @param {object} calculatorParams
 * @returns {string}
 */
export function formatArgs(calculatorParams) {
    return Object.entries(calculatorParams)
        .filter(([key, value]) => value !== null && value !== undefined)
        .map(([key, value]) => {
            if (key === 'hand') return `hand=Hand.${value}`;
            if (key === 'profile') return `profile=WormProfile.${value}`;
            if (key === 'worm_type') return `worm_type=WormType.${value.toUpperCase()}`;
            if (typeof value === 'boolean') return `${key}=${value ? 'True' : 'False'}`;
            return `${key}=${value}`;
        })
        .join(', ');
}
