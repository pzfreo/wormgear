"""Bore calculation utilities for worm gear designs.

These are pure calculation functions that don't depend on build123d geometry.
Used by both the calculator (web) and geometry (CLI) modules.
"""

from typing import Optional, Tuple


def calculate_default_bore(pitch_diameter: float, root_diameter: float) -> tuple[float, bool]:
    """
    Calculate a sensible default bore diameter based on gear dimensions.

    Uses approximately 25% of pitch diameter, but constrained by:
    - Minimum: 2mm (practical minimum for small gears)
    - Maximum: Leaves at least 25% of root diameter as rim, or 1mm minimum

    The result is rounded to nice values:
    - Below 6mm: round to nearest 0.5mm
    - 6-12mm: round to nearest 0.5mm
    - 12mm and above: round to nearest 1mm

    Note: DIN 6885 keyways only cover bores >= 6mm. For smaller bores,
    keyways will be omitted automatically.

    Args:
        pitch_diameter: Gear pitch diameter in mm
        root_diameter: Gear root diameter in mm

    Returns:
        Tuple of (bore_diameter, has_warning) where:
        - bore_diameter: Recommended bore in mm (rounded), or None if impossible
        - has_warning: True if rim is thin (< 1.5mm) - part may need care
    """
    # Target ~25% of pitch diameter
    target = pitch_diameter * 0.25

    # Minimum practical bore is 2mm
    min_bore = 2.0

    # Maximum bore: leave at least 25% of root as rim, with 1mm absolute minimum
    # (root_diameter - max_bore) / 2 >= max(root_diameter * 0.25 / 2, 1.0)
    # Simplified: max_bore = root_diameter * 0.75 - but at least leave 1mm rim each side
    min_rim = max(root_diameter * 0.125, 1.0)  # 12.5% of root, min 1mm per side
    max_bore = root_diameter - 2 * min_rim

    # If gear is too small for any bore, return None
    if max_bore < min_bore:
        return (None, False)

    # Clamp to valid range
    bore = max(min_bore, min(target, max_bore))

    # Round to nice values
    if bore < 12:
        # Round to nearest 0.5mm for small bores
        bore = round(bore * 2) / 2
    else:
        # Round to nearest 1mm for larger bores
        bore = round(bore)

    # Final clamp after rounding
    bore = max(min_bore, min(bore, max_bore))

    # Check if rim is thin (warning threshold: < 1.5mm)
    actual_rim = (root_diameter - bore) / 2
    has_warning = actual_rim < 1.5

    return (bore, has_warning)
