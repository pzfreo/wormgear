/**
 * Parameter Handler Module
 *
 * Handles parameter extraction from UI and formatting for Python calls.
 */

/**
 * Get design function name for given mode
 * @param {string} mode - Calculation mode
 * @returns {string} Python function name
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
 * Get all input parameters from UI
 * @param {string} mode - Calculation mode
 * @returns {{calculator: object, manufacturing: object, bore: object}}
 */
export function getInputs(mode) {
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
        worm_keyway: document.getElementById('worm-anti-rotation').value,
        wheel_bore_type: document.getElementById('wheel-bore-type').value,
        wheel_bore_diameter: safeParseFloat(document.getElementById('wheel-bore-diameter').value),
        wheel_keyway: document.getElementById('wheel-anti-rotation').value
    };

    return {
        calculator: calculatorParams,
        manufacturing: manufacturingParams,
        bore: boreParams
    };
}

/**
 * Format calculator parameters for Python function call
 * @param {object} calculatorParams - Calculator parameters
 * @returns {string} Formatted argument string for Python
 */
export function formatArgs(calculatorParams) {
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
