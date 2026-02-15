/**
 * Shared formatting utilities for the wormgear web UI.
 *
 * Consolidates number formatting, profile labels, base64 conversion,
 * bore display formatting, and spec sheet row building that were
 * previously duplicated across app.js, generator-ui.js, and viewer-3d.js.
 */

// ---------------------------------------------------------------------------
// Number formatting
// ---------------------------------------------------------------------------

/** Format a number to fixed decimals, or em-dash if null/undefined. */
export const fmt = (val, d = 2) => val != null ? Number(val).toFixed(d) : '\u2014';

/** Format a value as "X.XX mm", or em-dash if null/undefined. */
export const fmtMm = (val, d = 2) => val != null ? `${Number(val).toFixed(d)} mm` : '\u2014';

/** Format a value as "X.X\u00b0", or em-dash if null/undefined. */
export const fmtDeg = (val, d = 1) => val != null ? `${Number(val).toFixed(d)}\u00b0` : '\u2014';

// ---------------------------------------------------------------------------
// Profile labels
// ---------------------------------------------------------------------------

export const PROFILE_LABELS = {
    'ZA': 'ZA (straight flanks)',
    'ZK': 'ZK (convex flanks)',
    'ZI': 'ZI (involute)',
};

// ---------------------------------------------------------------------------
// Base64 conversion
// ---------------------------------------------------------------------------

/**
 * Decode a base64 string to an ArrayBuffer.
 * Used by the 3D viewer to parse 3MF/STL mesh data.
 */
export function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const buffer = new ArrayBuffer(binary.length);
    const view = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
        view[i] = binary.charCodeAt(i);
    }
    return buffer;
}

// ---------------------------------------------------------------------------
// Bore formatting
// ---------------------------------------------------------------------------

/**
 * Format a bore feature object into a human-readable display string.
 *
 * @param {object} feature - Feature object with bore_type, bore_diameter_mm, anti_rotation
 * @param {object} [options] - Options
 * @param {boolean} [options.verbose=true] - Use verbose anti-rotation labels (e.g. "DIN 6885 keyway" vs "keyway")
 * @returns {string|null} Display string, or null if no bore info to show
 */
export function formatBoreStr(feature, { verbose = true } = {}) {
    if (!feature) return null;

    if (feature.bore_type === 'none') {
        return verbose ? 'Solid (no bore)' : 'Solid';
    }

    if (feature.bore_type === 'custom' && feature.bore_diameter_mm) {
        let s = `${fmt(feature.bore_diameter_mm, 1)} mm`;
        if (feature.anti_rotation === 'DIN6885') {
            s += verbose ? ' + DIN 6885 keyway' : ' + keyway';
        } else if (feature.anti_rotation === 'ddcut') {
            s += ' + DD-cut';
        }
        return s;
    }

    return null;
}

// ---------------------------------------------------------------------------
// Spec sheet row builder
// ---------------------------------------------------------------------------

/**
 * Build the data rows for all spec sheet sections from a design object.
 *
 * Returns { overview, worm, wheel, assembly, shaft } where each is an
 * array of [label, value] pairs. Both renderSpecSheet (HTML) and
 * buildPDFDocument (jsPDF) consume these rows, keeping data logic in
 * one place and letting each caller handle presentation only.
 *
 * @param {object} design - Full design JSON object
 * @param {object} [output] - Calculator output (for recommended dims)
 * @returns {{ overview: Array, worm: Array, wheel: Array, assembly: Array, shaft: Array }}
 */
export function buildSpecRows(design, output = null) {
    const worm = design.worm || {};
    const wheel = design.wheel || {};
    const asm = design.assembly || {};
    const mfg = design.manufacturing || {};
    const features = design.features || {};
    const wormType = worm.type || 'cylindrical';

    const profileLabel = PROFILE_LABELS[mfg.profile] || mfg.profile || 'ZA';

    // --- Overview ---
    const overview = [
        ['Ratio', `${asm.ratio}:1`],
        ['Module', fmtMm(worm.module_mm, 3)],
        ['Centre Distance', fmtMm(asm.centre_distance_mm)],
        ['Hand', (asm.hand || 'right').charAt(0).toUpperCase() + (asm.hand || 'right').slice(1).toLowerCase()],
        ['Profile', profileLabel],
    ];
    if (wormType === 'globoid') overview.push(['Worm Type', 'Globoid']);

    // --- Worm ---
    const wormRows = [
        ['Tip Diameter', fmtMm(worm.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(worm.pitch_diameter_mm)],
        ['Root Diameter', fmtMm(worm.root_diameter_mm)],
        ['Lead', fmtMm(worm.lead_mm, 3)],
        ['Lead Angle', fmtDeg(worm.lead_angle_deg)],
        ['Starts', worm.num_starts],
    ];
    if (mfg.worm_length_mm) {
        const recWormLen = output?.recommended_worm_length_mm;
        const isCustomWormLen = recWormLen != null && Math.abs(mfg.worm_length_mm - recWormLen) > 0.01;
        const wormLenNote = isCustomWormLen
            ? `${fmt(recWormLen, 1)} mm recommended`
            : 'recommended';
        wormRows.push(['Length', `${fmt(mfg.worm_length_mm, 1)} mm <span class="spec-note">(${wormLenNote})</span>`]);
    }
    if (wormType === 'globoid' && worm.throat_curvature_radius_mm) {
        wormRows.push(['Throat Pitch Radius', fmtMm(worm.throat_curvature_radius_mm)]);
    }
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        wormRows.push(['Throat Reduction', fmtMm(worm.throat_reduction_mm)]);
    }

    // --- Wheel ---
    const wheelRows = [
        ['Tip Diameter', fmtMm(wheel.tip_diameter_mm)],
        ['Pitch Diameter', fmtMm(wheel.pitch_diameter_mm)],
        ['Root Diameter', fmtMm(wheel.root_diameter_mm)],
        ['Teeth', wheel.num_teeth],
    ];
    if (mfg.wheel_width_mm) {
        const recWheelWidth = output?.recommended_wheel_width_mm;
        const isCustomWheelWidth = recWheelWidth != null && Math.abs(mfg.wheel_width_mm - recWheelWidth) > 0.01;
        const wheelWidthNote = isCustomWheelWidth
            ? `${fmt(recWheelWidth, 1)} mm recommended`
            : 'recommended';
        wheelRows.push(['Face Width', `${fmt(mfg.wheel_width_mm, 1)} mm <span class="spec-note">(${wheelWidthNote})</span>`]);
    }
    if (wheel.helix_angle_deg) {
        wheelRows.push(['Helix Angle', fmtDeg(wheel.helix_angle_deg)]);
    }
    wheelRows.push(['Throated', mfg.throated_wheel ? 'Yes' : 'No']);

    // Min OD at throat for globoid
    if (wormType === 'globoid' && worm.throat_reduction_mm) {
        const arcR = worm.tip_diameter_mm / 2 - worm.throat_reduction_mm;
        const margin = worm.addendum_mm + 0.5 * wheel.addendum_mm;
        const minBlankR = asm.centre_distance_mm - arcR + margin;
        const throatOD = 2 * Math.min(wheel.tip_diameter_mm / 2, minBlankR);
        wheelRows.push(['Min OD at Throat', fmtMm(throatOD)]);
    }

    // --- Assembly ---
    const assembly = [
        ['Pressure Angle', fmtDeg(asm.pressure_angle_deg)],
        ['Backlash', fmtMm(asm.backlash_mm, 3)],
        ['Efficiency', asm.efficiency_percent != null ? `~${Math.round(asm.efficiency_percent)}%` : '\u2014'],
        ['Self-Locking', asm.self_locking ? 'Yes' : 'No'],
    ];

    // --- Shaft Interface ---
    const shaft = [];
    const wormBoreStr = formatBoreStr(features.worm);
    if (wormBoreStr) shaft.push(['Worm Bore', wormBoreStr]);

    const wheelBoreStr = formatBoreStr(features.wheel);
    if (wheelBoreStr) shaft.push(['Wheel Bore', wheelBoreStr]);

    return { overview, worm: wormRows, wheel: wheelRows, assembly, shaft };
}
