"""
Engineering constants for wormgear calculations.

This module centralizes all numerical constants used in the calculator and
validation modules. Each constant is documented with its source (DIN standard,
ISO standard, or engineering best practice).

MODIFICATION GUIDELINES:
- Never change DIN/ISO constants without updating the standard reference
- Engineering practice constants may be adjusted based on experience
- Add new constants here rather than hardcoding in functions
- Always include units in constant names (_MM, _DEG, _PERCENT)

Constants are grouped by category:
- DIN 3975: Worm gear geometry standards
- DIN 3996: Worm gear load capacity standards
- DIN 6885: Keyway dimensions
- ISO 54: Standard modules
- Engineering practice: Industry best practices (not standardized)
- Manufacturing: Practical manufacturing constraints
"""

from typing import Tuple, Dict

# =============================================================================
# DIN 3975 - Worm Gear Geometry Standards
# =============================================================================

# Standard pressure angles per DIN 3975 Table 1
STANDARD_PRESSURE_ANGLES_DEG: Tuple[float, ...] = (14.5, 20.0, 25.0)

# Default pressure angle - most common in industry
DEFAULT_PRESSURE_ANGLE_DEG: float = 20.0  # DIN 3975 recommends 20° for general use

# Standard clearance factor (bottom clearance = c × module)
# DIN 3975 §5.3: c = 0.2 to 0.3, with 0.25 as typical
CLEARANCE_FACTOR_DEFAULT: float = 0.25

# Lead angle limits per DIN 3975 §4.2
LEAD_ANGLE_MIN_DEG: float = 1.0    # Below this: manufacturing very difficult
LEAD_ANGLE_MAX_DEG: float = 45.0   # Above this: impractical geometry

# =============================================================================
# DIN 3996 - Worm Gear Load Capacity Standards
# =============================================================================

# Self-locking threshold per DIN 3996 §7.4
# Below this lead angle, friction prevents backdrive under typical conditions
SELF_LOCKING_THRESHOLD_DEG: float = 6.0

# Efficiency thresholds for warnings
# DIN 3996 notes that η < 30% causes significant heat generation
EFFICIENCY_WARNING_VERY_LOW_PERCENT: float = 30.0
EFFICIENCY_WARNING_LOW_PERCENT: float = 50.0

# Default friction coefficient for efficiency calculations
# DIN 3996 Table 5: Bronze on steel, oil lubricated
FRICTION_COEFFICIENT_DEFAULT: float = 0.05

# =============================================================================
# ISO 54 / DIN 780 - Standard Modules
# =============================================================================

# Standard module series per ISO 54 (subset commonly used for worm gears)
STANDARD_MODULES_MM: Tuple[float, ...] = (
    0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
    1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0,
    3.5, 4.0, 4.5, 5.0, 5.5, 6.0,
    7.0, 8.0, 9.0, 10.0
)

# Tolerance for "close to standard" module check
MODULE_STANDARD_TOLERANCE_PERCENT: float = 10.0

# =============================================================================
# Engineering Best Practice (Not Standardized)
# =============================================================================

# Wheel face width recommendations
# Source: Dudley's Handbook of Practical Gear Design, empirical guidelines
WHEEL_WIDTH_FACTOR_RECOMMENDED: float = 1.3    # width = 1.3 × worm_pitch_dia
WHEEL_WIDTH_FACTOR_MIN: float = 8.0            # width >= module × 8.0
WHEEL_WIDTH_FACTOR_MAX: float = 12.0           # width <= module × 12.0

# Worm length recommendations
# Source: Industry practice for ensuring full tooth engagement
WORM_LENGTH_SAFETY_MM: float = 1.0             # Additional length margin
WORM_LENGTH_FACTOR: float = 2.0                # length = face_width + 2×lead + safety

# Worm proportions (pitch_diameter / module ratio)
# Source: Machinery's Handbook, practical design guidelines
WORM_RATIO_MIN: float = 5.0    # Below: worm core too thin, weak
WORM_RATIO_MAX: float = 20.0   # Above: worm too thick, inefficient material use

# Lead angle warning thresholds (engineering judgment)
LEAD_ANGLE_WARNING_VERY_LOW_DEG: float = 3.0   # Very low efficiency expected
LEAD_ANGLE_WARNING_LOW_DEG: float = 5.0        # Low efficiency expected
LEAD_ANGLE_WARNING_HIGH_DEG: float = 25.0      # Self-locking unlikely

# Contact ratio minimum for smooth operation
# Source: AGMA 6022, gear design best practices
CONTACT_RATIO_MIN: float = 1.2

# =============================================================================
# Manufacturing Constraints
# =============================================================================

# Minimum rim thickness before structural concerns
# Source: Practical machining experience, material-dependent
MIN_RIM_THICKNESS_MM: float = 0.5              # Below: high failure risk
WARN_RIM_WORM_MM: float = 1.5                  # Worm warning threshold
WARN_RIM_WHEEL_MM: float = 2.0                 # Wheel warning threshold

# Minimum thread width for manufacturability
# Source: CNC machining practical limits
MIN_THREAD_WIDTH_MM: float = 0.1

# Small bore threshold (below which keyways aren't practical)
# Source: DIN 6885 doesn't define keyways below 6mm
SMALL_BORE_THRESHOLD_MM: float = 2.0
KEYWAY_MIN_BORE_MM: float = 6.0                # DIN 6885 minimum

# Bore sizing recommendations
# Source: Standard shaft/bore fitting practice
BORE_TARGET_FACTOR: float = 0.25               # bore ≈ 25% of pitch diameter
BORE_THIN_RIM_WARNING_MM: float = 1.5          # Warn if rim < this

# =============================================================================
# Globoid Worm Specific
# =============================================================================

# Throat reduction warning threshold
# Source: Engineering judgment - aggressive reduction affects strength
THROAT_REDUCTION_WARNING_PERCENT: float = 20.0

# Default worm length factor for globoid
GLOBOID_LENGTH_FACTOR: float = 1.3             # length = pitch_dia × 1.3

# =============================================================================
# Virtual Hobbing
# =============================================================================

# Hobbing step limits
HOBBING_STEPS_MIN: int = 6                     # Below: geometry too coarse
HOBBING_STEPS_MAX: int = 1000                  # Above: memory exhaustion risk

# Hobbing presets (steps, description)
HOBBING_PRESETS: Dict[str, Dict] = {
    "preview": {"steps": 36, "description": "Quick preview (15-30s native, 1-3min WASM)"},
    "balanced": {"steps": 72, "description": "Balanced quality (30-60s native, 3-6min WASM)"},
    "high": {"steps": 144, "description": "High quality (1-2min native, 6-12min WASM)"},
    "ultra": {"steps": 360, "description": "Ultra quality (3-5min native, 15-30min WASM)"},
}

# Globoid hob optimization - auto-reduce steps
GLOBOID_HOB_MAX_STEPS: int = 36                # Reduce for globoid hobs

# =============================================================================
# Geometry Generation
# =============================================================================

# Minimum sections for loft operations
MIN_LOFT_SECTIONS: int = 2

# Default sections per turn for helix generation
DEFAULT_SECTIONS_PER_TURN: int = 36

# Taper factor minimum (prevents degenerate thread profiles)
MIN_TAPER_FACTOR: float = 0.05
