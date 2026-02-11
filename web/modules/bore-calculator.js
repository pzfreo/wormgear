/**
 * Bore Calculator Module
 *
 * Displays bore recommendations from Python calculator and
 * manages UI for bore type selection and anti-rotation methods.
 *
 * NOTE: All bore calculations are done in Python (single source of truth).
 * This module only handles UI display and user interaction.
 *
 * VERSION: 2025-01-28-python-source
 */

console.log('[Bore Calculator] Module loaded - VERSION: 2025-01-28-python-source');

// Store bore recommendations from Python
let recommendedWormBore = null;
let recommendedWheelBore = null;

// Loading guard: when true, suppress auto-fill of bore diameters
// and auto-selection of anti-rotation defaults.
// Set by loadDesignIntoDesignTab() during JSON round-trip loading.
let _isLoading = false;

/**
 * Set loading state to suppress auto-fill and auto-select during JSON round-trip.
 * @param {boolean} loading - true to suppress, false to restore normal behavior
 */
export function setLoadingState(loading) {
    _isLoading = loading;
}

/**
 * Get current recommended bore values (from Python)
 * @returns {{worm: number|null, wheel: number|null}}
 */
export function getCalculatedBores() {
    return {
        worm: recommendedWormBore?.diameter_mm ?? null,
        wheel: recommendedWheelBore?.diameter_mm ?? null
    };
}

/**
 * Update bore displays using Python's recommended values
 * @param {object} design - Current gear design object
 * @param {object} wormBore - Python's recommended worm bore {diameter_mm, has_warning, too_small_for_keyway}
 * @param {object} wheelBore - Python's recommended wheel bore {diameter_mm, has_warning, too_small_for_keyway}
 */
export function updateBoreDisplaysAndDefaults(design, wormBore, wheelBore) {
    // Store Python's recommendations
    recommendedWormBore = wormBore;
    recommendedWheelBore = wheelBore;

    if (!design || !design.worm || !design.wheel) {
        document.getElementById('worm-bore-info').style.display = 'none';
        document.getElementById('wheel-bore-info').style.display = 'none';
        return;
    }

    // Show recommended values from Python
    document.getElementById('worm-bore-info').style.display = 'block';
    document.getElementById('wheel-bore-info').style.display = 'block';

    // Display worm bore recommendation
    const wormBoreEl = document.getElementById('worm-bore-recommended');
    if (wormBore?.diameter_mm != null) {
        let html = `${wormBore.diameter_mm.toFixed(1)} mm`;
        const warnings = [];
        if (wormBore.too_small_for_keyway) {
            warnings.push('too small for DIN 6885');
        }
        if (wormBore.has_warning) {
            warnings.push('thin rim');
        }
        if (warnings.length > 0) {
            html += ` <span style="color: #c75; font-style: italic;">(${warnings.join(', ')})</span>`;
        }
        wormBoreEl.innerHTML = html;
    } else {
        wormBoreEl.innerHTML = `<span style="color: #c75; font-style: italic;">Gear too small for bore</span>`;
    }

    // Display wheel bore recommendation
    const wheelBoreEl = document.getElementById('wheel-bore-recommended');
    if (wheelBore?.diameter_mm != null) {
        let html = `${wheelBore.diameter_mm.toFixed(1)} mm`;
        const warnings = [];
        if (wheelBore.too_small_for_keyway) {
            warnings.push('too small for DIN 6885');
        }
        if (wheelBore.has_warning) {
            warnings.push('thin rim');
        }
        if (warnings.length > 0) {
            html += ` <span style="color: #c75; font-style: italic;">(${warnings.join(', ')})</span>`;
        }
        wheelBoreEl.innerHTML = html;
    } else {
        wheelBoreEl.innerHTML = `<span style="color: #c75; font-style: italic;">Gear too small for bore</span>`;
    }

    // Update anti-rotation options
    updateAntiRotationOptions();
}

/**
 * Update anti-rotation method dropdowns based on bore sizes
 */
export function updateAntiRotationOptions() {
    const wormBoreDia = recommendedWormBore?.diameter_mm ?? null;
    const wheelBoreDia = recommendedWheelBore?.diameter_mm ?? null;

    console.log('[Anti-Rotation] updateAntiRotationOptions called, wormBore=', wormBoreDia, 'wheelBore=', wheelBoreDia);

    // Update worm anti-rotation options
    updateAntiRotationForPart('worm', wormBoreDia);
    // Update wheel anti-rotation options
    updateAntiRotationForPart('wheel', wheelBoreDia);
}

/**
 * Update anti-rotation options for a specific part (worm or wheel)
 * @param {string} partName - 'worm' or 'wheel'
 * @param {number|null} recommendedBore - Python's recommended bore size (null if gear too small)
 */
function updateAntiRotationForPart(partName, recommendedBore) {
    const boreType = document.getElementById(`${partName}-bore-type`).value;
    const antiRotSelect = document.getElementById(`${partName}-anti-rotation`);
    const antiRotGroup = document.getElementById(`${partName}-anti-rotation-group`);

    if (boreType === 'none') {
        // No bore = no anti-rotation needed
        antiRotGroup.style.display = 'none';
        return;
    }

    // If gear is too small for bore, hide anti-rotation options
    if (recommendedBore === null && boreType === 'auto') {
        antiRotGroup.style.display = 'none';
        return;
    }

    antiRotGroup.style.display = 'block';

    // Get effective bore size
    let effectiveBore = recommendedBore;
    if (boreType === 'custom') {
        effectiveBore = parseFloat(document.getElementById(`${partName}-bore-diameter`).value) || recommendedBore;
    }

    console.log(`[Anti-Rotation] ${partName}: bore=${effectiveBore}mm, current=${antiRotSelect.value}`);

    // Skip if bore not available
    if (!effectiveBore || effectiveBore <= 0) {
        console.log(`[Anti-Rotation] ${partName}: skipping (no bore available)`);
        return;
    }

    // Enable/disable DIN 6885 based on bore size
    const din6885Option = Array.from(antiRotSelect.options).find(opt => opt.value === 'DIN6885');
    if (din6885Option) {
        din6885Option.disabled = effectiveBore < 6.0;
        din6885Option.text = effectiveBore < 6.0
            ? 'DIN 6885 Keyway (requires bore ≥ 6mm)'
            : 'DIN 6885 Keyway';
    }

    // Auto-select sensible default
    // Always enforce hard constraint: DIN6885 requires bore >= 6mm
    if (antiRotSelect.value === 'DIN6885' && effectiveBore < 6.0) {
        console.log(`[Anti-Rotation] ${partName}: switching from DIN6885 to ddcut (bore too small)`);
        antiRotSelect.value = 'ddcut'; // Switch to ddcut for small bores
    } else if (!_isLoading) {
        // Only auto-select defaults during normal user interaction, not during JSON loading
        if (effectiveBore >= 6.0 && antiRotSelect.value === 'none') {
            // Default to DIN 6885 for bores >= 6mm (engineers expect a keyed bore)
            console.log(`[Anti-Rotation] ${partName}: setting default to DIN6885 (bore ${effectiveBore}mm)`);
            antiRotSelect.value = 'DIN6885';
        } else if (effectiveBore < 6.0 && (antiRotSelect.value === '' || antiRotSelect.value === 'none')) {
            // Default to ddcut for small bores
            console.log(`[Anti-Rotation] ${partName}: setting default to ddcut (bore ${effectiveBore}mm)`);
            antiRotSelect.value = 'ddcut';
        }
    }
}

/**
 * Setup event listeners for bore controls
 */
export function setupBoreEventListeners() {
    // Worm bore type change
    document.getElementById('worm-bore-type').addEventListener('change', (e) => {
        const customDiv = document.getElementById('worm-bore-custom');
        customDiv.style.display = e.target.value === 'custom' ? 'block' : 'none';

        // Set custom bore to recommended value when switching to custom
        // (skip during JSON loading to preserve loaded values)
        if (e.target.value === 'custom' && recommendedWormBore?.diameter_mm && !_isLoading) {
            document.getElementById('worm-bore-diameter').value = recommendedWormBore.diameter_mm.toFixed(1);
        }

        updateAntiRotationOptions();
    });

    // Wheel bore type change
    document.getElementById('wheel-bore-type').addEventListener('change', (e) => {
        const customDiv = document.getElementById('wheel-bore-custom');
        customDiv.style.display = e.target.value === 'custom' ? 'block' : 'none';

        if (e.target.value === 'custom' && recommendedWheelBore?.diameter_mm && !_isLoading) {
            document.getElementById('wheel-bore-diameter').value = recommendedWheelBore.diameter_mm.toFixed(1);
        }

        updateAntiRotationOptions();
    });

    // Custom bore diameter changes
    document.getElementById('worm-bore-diameter').addEventListener('change', updateAntiRotationOptions);
    document.getElementById('wheel-bore-diameter').addEventListener('change', updateAntiRotationOptions);
}

// Legacy export for compatibility - no longer calculates, just returns stored value
export function calculateBoreSize(pitchDiameter, rootDiameter) {
    console.warn('[Bore Calculator] calculateBoreSize is deprecated - calculations now done in Python');
    // Return a simple approximation for backward compatibility
    const target = pitchDiameter * 0.25;
    const max = rootDiameter - 2.0;
    let bore = Math.min(target, max);
    bore = Math.max(2.0, bore);
    return bore >= 12 ? Math.round(bore) : Math.round(bore * 2) / 2;
}
