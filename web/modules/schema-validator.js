/**
 * Runtime Schema Validation for JS<->Python Bridge
 *
 * Validates data at the boundary between JavaScript and Python.
 * Uses simple runtime checks (no external dependencies like Zod).
 *
 * This ensures:
 * 1. Data sent TO Python is valid
 * 2. Data received FROM Python matches expected schema
 */

// ============================================================================
// Enum Validators
// ============================================================================

const VALID_HANDS = ['right', 'left'];
const VALID_PROFILES = ['ZA', 'ZK', 'ZI'];
const VALID_WORM_TYPES = ['cylindrical', 'globoid'];
const VALID_BORE_TYPES = ['none', 'custom'];  // 'custom' with null diameter = auto-calculate
const VALID_ANTI_ROTATION = ['none', 'DIN6885', 'ddcut'];
const VALID_MODES = ['from-module', 'from-centre-distance', 'from-wheel', 'envelope', 'from-arc-angle'];
const VALID_SEVERITIES = ['error', 'warning', 'info'];

// ============================================================================
// Validation Helpers
// ============================================================================

/**
 * @param {any} value
 * @param {string} name
 * @returns {number}
 */
function requireNumber(value, name) {
    if (typeof value !== 'number' || isNaN(value)) {
        throw new Error(`${name} must be a number, got ${typeof value}`);
    }
    return value;
}

/**
 * @param {any} value
 * @param {string} name
 * @returns {number|null}
 */
function optionalNumber(value, name) {
    if (value === null || value === undefined) return null;
    return requireNumber(value, name);
}

/**
 * @param {any} value
 * @param {string} name
 * @returns {string}
 */
function requireString(value, name) {
    if (typeof value !== 'string') {
        throw new Error(`${name} must be a string, got ${typeof value}`);
    }
    return value;
}

/**
 * @param {any} value
 * @param {string[]} allowed
 * @param {string} name
 * @returns {string}
 */
function requireEnum(value, allowed, name) {
    const str = requireString(value, name);
    if (!allowed.includes(str)) {
        throw new Error(`${name} must be one of [${allowed.join(', ')}], got "${str}"`);
    }
    return str;
}

/**
 * @param {any} value
 * @param {string} name
 * @returns {boolean}
 */
function requireBoolean(value, name) {
    if (typeof value !== 'boolean') {
        throw new Error(`${name} must be a boolean, got ${typeof value}`);
    }
    return value;
}

/**
 * @param {any} value
 * @param {string} name
 * @returns {number}
 */
function requireInteger(value, name) {
    const num = requireNumber(value, name);
    if (!Number.isInteger(num)) {
        throw new Error(`${name} must be an integer, got ${num}`);
    }
    return num;
}

// ============================================================================
// Input Validation (JS -> Python)
// ============================================================================

/**
 * Validate bore settings before sending to Python
 * @param {object} bore
 * @returns {object} Validated bore settings
 */
export function validateBoreSettings(bore) {
    if (!bore) return {
        worm_bore_type: 'none',
        worm_bore_diameter: null,
        worm_keyway: 'none',
        wheel_bore_type: 'none',
        wheel_bore_diameter: null,
        wheel_keyway: 'none'
    };

    return {
        worm_bore_type: requireEnum(bore.worm_bore_type || 'none', VALID_BORE_TYPES, 'worm_bore_type'),
        worm_bore_diameter: optionalNumber(bore.worm_bore_diameter, 'worm_bore_diameter'),
        worm_keyway: requireEnum(bore.worm_keyway || 'none', VALID_ANTI_ROTATION, 'worm_keyway'),
        wheel_bore_type: requireEnum(bore.wheel_bore_type || 'none', VALID_BORE_TYPES, 'wheel_bore_type'),
        wheel_bore_diameter: optionalNumber(bore.wheel_bore_diameter, 'wheel_bore_diameter'),
        wheel_keyway: requireEnum(bore.wheel_keyway || 'none', VALID_ANTI_ROTATION, 'wheel_keyway')
    };
}

/**
 * Validate manufacturing settings before sending to Python
 * @param {object} mfg
 * @returns {object} Validated manufacturing settings
 */
export function validateManufacturingSettings(mfg) {
    if (!mfg) return {
        use_recommended_dims: true,
        worm_length_mm: null,
        wheel_width_mm: null
    };

    const result = {
        use_recommended_dims: typeof mfg.use_recommended_dims === 'boolean' ? mfg.use_recommended_dims : true,
        worm_length_mm: optionalNumber(mfg.worm_length_mm, 'worm_length_mm'),
        wheel_width_mm: optionalNumber(mfg.wheel_width_mm, 'wheel_width_mm'),
        trim_to_min_engagement: typeof mfg.trim_to_min_engagement === 'boolean' ? mfg.trim_to_min_engagement : false
    };

    // virtual_hobbing and hobbing_steps are optional (may come from older share links)
    if (mfg.virtual_hobbing !== undefined) {
        result.virtual_hobbing = typeof mfg.virtual_hobbing === 'boolean' ? mfg.virtual_hobbing : false;
    }
    if (mfg.hobbing_steps !== undefined) {
        result.hobbing_steps = typeof mfg.hobbing_steps === 'number' ? mfg.hobbing_steps : 72;
    }

    return result;
}

/**
 * Validate complete calculator inputs before sending to Python
 * @param {object} inputs - Raw inputs from UI
 * @returns {object} Validated inputs ready for JSON.stringify
 * @throws {Error} If validation fails
 */
export function validateCalculatorInputs(inputs) {
    const validated = {
        mode: requireEnum(inputs.mode, VALID_MODES, 'mode'),
        pressure_angle: requireNumber(inputs.pressure_angle, 'pressure_angle'),
        backlash: requireNumber(inputs.backlash, 'backlash'),
        num_starts: requireInteger(inputs.num_starts, 'num_starts'),
        hand: requireEnum(inputs.hand?.toLowerCase() || 'right', VALID_HANDS, 'hand'),
        profile_shift: requireNumber(inputs.profile_shift ?? 0, 'profile_shift'),
        profile: requireEnum(inputs.profile?.toUpperCase() || 'ZA', VALID_PROFILES, 'profile'),
        worm_type: requireEnum(inputs.worm_type?.toLowerCase() || 'cylindrical', VALID_WORM_TYPES, 'worm_type'),
        throat_reduction: requireNumber(inputs.throat_reduction ?? 0, 'throat_reduction'),
        throat_arc_angle: requireNumber(inputs.throat_arc_angle ?? 0, 'throat_arc_angle'),
        wheel_throated: typeof inputs.wheel_throated === 'boolean' ? inputs.wheel_throated : false,
        bore: validateBoreSettings(inputs.bore),
        manufacturing: validateManufacturingSettings(inputs.manufacturing)
    };

    // Add mode-specific parameters
    if (inputs.module !== null && inputs.module !== undefined) {
        validated.module = requireNumber(inputs.module, 'module');
    }
    if (inputs.ratio !== null && inputs.ratio !== undefined) {
        validated.ratio = requireInteger(inputs.ratio, 'ratio');
    }
    if (inputs.centre_distance !== null && inputs.centre_distance !== undefined) {
        validated.centre_distance = requireNumber(inputs.centre_distance, 'centre_distance');
    }
    if (inputs.worm_od !== null && inputs.worm_od !== undefined) {
        validated.worm_od = requireNumber(inputs.worm_od, 'worm_od');
    }
    if (inputs.wheel_od !== null && inputs.wheel_od !== undefined) {
        validated.wheel_od = requireNumber(inputs.wheel_od, 'wheel_od');
    }
    if (inputs.target_lead_angle !== null && inputs.target_lead_angle !== undefined) {
        validated.target_lead_angle = requireNumber(inputs.target_lead_angle, 'target_lead_angle');
    }
    if (inputs.od_as_maximum !== undefined) {
        validated.od_as_maximum = !!inputs.od_as_maximum;
    }
    if (inputs.use_standard_module !== undefined) {
        validated.use_standard_module = !!inputs.use_standard_module;
    }
    if (inputs.wheel_tip_reduction !== null && inputs.wheel_tip_reduction !== undefined) {
        validated.wheel_tip_reduction = requireNumber(inputs.wheel_tip_reduction, 'wheel_tip_reduction');
    }
    if (inputs.relief_groove !== null && inputs.relief_groove !== undefined) {
        const rg = inputs.relief_groove;
        validated.relief_groove = {
            type: requireEnum(rg.type || 'din76', ['din76', 'full-radius'], 'relief_groove.type'),
            width_mm: optionalNumber(rg.width_mm, 'relief_groove.width_mm'),
            depth_mm: optionalNumber(rg.depth_mm, 'relief_groove.depth_mm'),
            radius_mm: optionalNumber(rg.radius_mm, 'relief_groove.radius_mm'),
        };
    }

    return validated;
}

// ============================================================================
// Output Validation (Python -> JS)
// ============================================================================

/**
 * Validate calculator output from Python
 * @param {object} output - Parsed JSON from Python
 * @returns {object} Validated output
 * @throws {Error} If validation fails
 */
export function validateCalculatorOutput(output) {
    if (!output || typeof output !== 'object') {
        throw new Error('Calculator output must be an object');
    }

    if (typeof output.success !== 'boolean') {
        throw new Error('Calculator output.success must be a boolean');
    }

    if (!output.success) {
        // Error response
        return {
            success: false,
            error: output.error || 'Unknown error'
        };
    }

    // Success response - validate required fields
    if (typeof output.design_json !== 'string') {
        throw new Error('Calculator output.design_json must be a string');
    }

    return {
        success: true,
        design_json: output.design_json,
        summary: output.summary || '',
        markdown: output.markdown || '',
        valid: typeof output.valid === 'boolean' ? output.valid : true,
        messages: Array.isArray(output.messages) ? output.messages : [],
        // Python-calculated bore recommendations
        recommended_worm_bore: output.recommended_worm_bore || null,
        recommended_wheel_bore: output.recommended_wheel_bore || null,
        // Wheel throat OD (minimum OD at engagement zone for globoid/throated wheels)
        wheel_throat_od_mm: output.wheel_throat_od_mm ?? null
    };
}

/**
 * Validate WormGearDesign structure from Python
 * @param {object} design - Parsed design JSON
 * @returns {object} Validated design
 * @throws {Error} If critical fields are missing
 */
export function validateWormGearDesign(design) {
    if (!design || typeof design !== 'object') {
        throw new Error('Design must be an object');
    }

    // Check required sections exist
    if (!design.worm || typeof design.worm !== 'object') {
        throw new Error('Design must have a worm section');
    }
    if (!design.wheel || typeof design.wheel !== 'object') {
        throw new Error('Design must have a wheel section');
    }
    if (!design.assembly || typeof design.assembly !== 'object') {
        throw new Error('Design must have an assembly section');
    }

    // Validate critical worm fields
    requireNumber(design.worm.module_mm, 'worm.module_mm');
    requireNumber(design.worm.pitch_diameter_mm, 'worm.pitch_diameter_mm');
    requireNumber(design.worm.tip_diameter_mm, 'worm.tip_diameter_mm');

    // Validate critical wheel fields
    requireNumber(design.wheel.module_mm, 'wheel.module_mm');
    requireNumber(design.wheel.pitch_diameter_mm, 'wheel.pitch_diameter_mm');
    requireInteger(design.wheel.num_teeth, 'wheel.num_teeth');

    // Validate critical assembly fields
    requireNumber(design.assembly.centre_distance_mm, 'assembly.centre_distance_mm');
    requireInteger(design.assembly.ratio, 'assembly.ratio');

    return design;
}

// ============================================================================
// Convenience wrapper
// ============================================================================

/**
 * Parse and validate calculator output from Python
 * @param {string} jsonString - JSON string from Python
 * @returns {{output: object, design: object|null}} Validated output and design
 */
export function parseCalculatorResponse(jsonString) {
    const output = validateCalculatorOutput(JSON.parse(jsonString));

    if (!output.success) {
        return { output, design: null };
    }

    const design = validateWormGearDesign(JSON.parse(output.design_json));
    return { output, design };
}
