/**
 * Bore Calculator Module
 *
 * Handles bore size calculations and anti-rotation method selection.
 * Auto-calculates recommended bore sizes (~25% of pitch diameter) and
 * manages UI for bore type selection and anti-rotation methods.
 *
 * VERSION: 2025-01-25-debug
 */

console.log('[Bore Calculator] Module loaded - VERSION: 2025-01-25-debug');

// Store calculated bore values
let calculatedWormBore = null;
let calculatedWheelBore = null;

/**
 * Calculate recommended bore diameter
 * @param {number} pitchDiameter - Pitch diameter in mm
 * @param {number} rootDiameter - Root diameter in mm
 * @returns {number} Recommended bore diameter in mm
 */
export function calculateBoreSize(pitchDiameter, rootDiameter) {
    // Target ~25% of pitch diameter
    const target = pitchDiameter * 0.25;
    // Constrained by root (leave at least 1mm rim)
    const max = rootDiameter - 2.0;
    let bore = Math.min(target, max);
    // Minimum 2mm
    bore = Math.max(2.0, bore);
    // Round to 0.5mm (small) or 1mm (large)
    return bore >= 12 ? Math.round(bore) : Math.round(bore * 2) / 2;
}

/**
 * Get current calculated bore values
 * @returns {{worm: number|null, wheel: number|null}}
 */
export function getCalculatedBores() {
    return {
        worm: calculatedWormBore,
        wheel: calculatedWheelBore
    };
}

/**
 * Update bore displays and calculate recommended values
 * @param {object} design - Current gear design object
 */
export function updateBoreDisplaysAndDefaults(design) {
    if (!design || !design.worm || !design.wheel) {
        document.getElementById('worm-bore-info').style.display = 'none';
        document.getElementById('wheel-bore-info').style.display = 'none';
        return;
    }

    const wormPitch = design.worm.pitch_diameter_mm;
    const wormRoot = design.worm.root_diameter_mm;
    const wheelPitch = design.wheel.pitch_diameter_mm;
    const wheelRoot = design.wheel.root_diameter_mm;

    if (!wormPitch || !wormRoot || !wheelPitch || !wheelRoot) {
        document.getElementById('worm-bore-info').style.display = 'none';
        document.getElementById('wheel-bore-info').style.display = 'none';
        return;
    }

    // Calculate and store
    calculatedWormBore = calculateBoreSize(wormPitch, wormRoot);
    calculatedWheelBore = calculateBoreSize(wheelPitch, wheelRoot);

    // Show recommended values
    document.getElementById('worm-bore-info').style.display = 'block';
    document.getElementById('wheel-bore-info').style.display = 'block';

    // Include mm and warning in the span content
    if (calculatedWormBore < 6.0) {
        document.getElementById('worm-bore-recommended').innerHTML =
            `${calculatedWormBore.toFixed(1)} mm <span style="color: #c75; font-style: italic;">(too small for DIN 6885)</span>`;
    } else {
        document.getElementById('worm-bore-recommended').textContent = `${calculatedWormBore.toFixed(1)} mm`;
    }

    if (calculatedWheelBore < 6.0) {
        document.getElementById('wheel-bore-recommended').innerHTML =
            `${calculatedWheelBore.toFixed(1)} mm <span style="color: #c75; font-style: italic;">(too small for DIN 6885)</span>`;
    } else {
        document.getElementById('wheel-bore-recommended').textContent = `${calculatedWheelBore.toFixed(1)} mm`;
    }

    // Update anti-rotation options
    updateAntiRotationOptions();
}

/**
 * Update anti-rotation method dropdowns based on bore sizes
 */
export function updateAntiRotationOptions() {
    console.log('[Anti-Rotation] updateAntiRotationOptions called, wormBore=', calculatedWormBore, 'wheelBore=', calculatedWheelBore);
    // Update worm anti-rotation options
    updateAntiRotationForPart('worm', calculatedWormBore);
    // Update wheel anti-rotation options
    updateAntiRotationForPart('wheel', calculatedWheelBore);
}

/**
 * Update anti-rotation options for a specific part (worm or wheel)
 * @param {string} partName - 'worm' or 'wheel'
 * @param {number} calculatedBore - Calculated bore size
 */
function updateAntiRotationForPart(partName, calculatedBore) {
    const boreType = document.getElementById(`${partName}-bore-type`).value;
    const antiRotSelect = document.getElementById(`${partName}-anti-rotation`);
    const antiRotGroup = document.getElementById(`${partName}-anti-rotation-group`);

    if (boreType === 'none') {
        // No bore = no anti-rotation needed
        antiRotGroup.style.display = 'none';
        return;
    }

    antiRotGroup.style.display = 'block';

    // Get effective bore size
    let effectiveBore = calculatedBore;
    if (boreType === 'custom') {
        effectiveBore = parseFloat(document.getElementById(`${partName}-bore-diameter`).value) || calculatedBore;
    }

    console.log(`[Anti-Rotation] ${partName}: bore=${effectiveBore}mm, current=${antiRotSelect.value}`);

    // Skip if bore not calculated yet
    if (!effectiveBore || effectiveBore <= 0) {
        console.log(`[Anti-Rotation] ${partName}: skipping (no bore calculated yet)`);
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
    if (antiRotSelect.value === 'DIN6885' && effectiveBore < 6.0) {
        console.log(`[Anti-Rotation] ${partName}: switching from DIN6885 to DD-cut (bore too small)`);
        antiRotSelect.value = 'DD-cut'; // Switch to DD-cut for small bores
    } else if (antiRotSelect.value === '' || antiRotSelect.value === 'none') {
        // Set initial default based on bore size
        const newValue = effectiveBore < 6.0 ? 'DD-cut' : 'DIN6885';
        console.log(`[Anti-Rotation] ${partName}: setting default to ${newValue} (bore ${effectiveBore}mm)`);
        antiRotSelect.value = newValue;
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

        // Set custom bore to calculated value when switching to custom
        if (e.target.value === 'custom' && calculatedWormBore) {
            document.getElementById('worm-bore-diameter').value = calculatedWormBore.toFixed(1);
        }

        updateAntiRotationOptions();
    });

    // Wheel bore type change
    document.getElementById('wheel-bore-type').addEventListener('change', (e) => {
        const customDiv = document.getElementById('wheel-bore-custom');
        customDiv.style.display = e.target.value === 'custom' ? 'block' : 'none';

        if (e.target.value === 'custom' && calculatedWheelBore) {
            document.getElementById('wheel-bore-diameter').value = calculatedWheelBore.toFixed(1);
        }

        updateAntiRotationOptions();
    });

    // Custom bore diameter changes
    document.getElementById('worm-bore-diameter').addEventListener('change', updateAntiRotationOptions);
    document.getElementById('wheel-bore-diameter').addEventListener('change', updateAntiRotationOptions);
}
