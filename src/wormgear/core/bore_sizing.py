"""Bore calculation utilities for worm gear designs.

These are pure calculation functions that don't depend on build123d geometry.
Used by both the calculator (web) and geometry (CLI) modules.
"""

from typing import Optional, Tuple


def calculate_default_bore(pitch_diameter: float, root_diameter: float) -> tuple[float, bool]:
    """
    Calculate a sensible default bore diameter based on gear dimensions.

    Uses approximately 25% of pitch diameter, but constrained by:
    - Minimum: 2mm (for structural integrity)
    - Maximum: Constrained by root diameter to leave adequate rim

    The minimum rim thickness is calculated as:
    - min_rim = max(root_diameter * 0.125, 1.0) mm per side

    The result is rounded to nice values:
    - Below 2mm: not used (minimum is 2mm)
    - 2-12mm: round to nearest 0.5mm
    - 12mm and above: round to nearest 1mm

    Note: DIN 6885 keyways only cover bores >= 6mm. For smaller bores,
    keyways will be omitted automatically.

    Args:
        pitch_diameter: Gear pitch diameter in mm
        root_diameter: Gear root diameter in mm

    Returns:
        Tuple of (bore_diameter, has_warning) where:
        - bore_diameter: Recommended bore in mm (rounded), or None if physically impossible
        - has_warning: True if rim is thin (< 1.5mm) - part may need care
    """
    # Minimum bore is 2mm for structural integrity
    min_bore = 2.0

    # If root diameter is invalid (negative or zero), no bore is possible
    if root_diameter <= 0:
        return (None, False)

    # Calculate minimum rim thickness: 12.5% of root diameter, but at least 1.0mm
    min_rim = max(root_diameter * 0.125, 1.0)

    # Maximum bore: leave min_rim on each side
    max_bore = root_diameter - (2 * min_rim)

    # If max_bore is less than min_bore, no bore is possible
    if max_bore < min_bore:
        return (None, False)

    # Target ~25% of pitch diameter
    target = pitch_diameter * 0.25

    # Constrain bore to valid range
    bore = max(min_bore, min(target, max_bore))

    # Round to nice values
    if bore < 12:
        # Round to nearest 0.5mm for small/medium bores
        bore = round(bore * 2) / 2
    else:
        # Round to nearest 1mm for larger bores
        bore = round(bore)

    # Ensure at least min_bore after rounding
    bore = max(min_bore, bore)

    # Check if bore fits within max allowed
    if bore > max_bore:
        return (None, False)

    # Calculate actual rim thickness
    actual_rim = (root_diameter - bore) / 2

    # If rim would be zero or negative, bore is impossible
    if actual_rim <= 0:
        return (None, False)

    # Warning if rim is thin (< 1.5mm)
    has_warning = actual_rim < 1.5

    return (bore, has_warning)
