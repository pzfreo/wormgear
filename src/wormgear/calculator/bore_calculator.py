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
    - Maximum: Constrained by root diameter to leave some rim

    The result is rounded to nice values:
    - Below 12mm: round to nearest 0.5mm
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
    # Minimum practical bore is 2mm
    min_bore = 2.0

    # If root diameter is less than min bore, no bore is possible
    if root_diameter <= min_bore:
        return (None, False)

    # Target ~25% of pitch diameter
    target = pitch_diameter * 0.25

    # Maximum bore: leave at least 1mm rim on each side
    max_bore = root_diameter - 2.0

    # If max_bore is less than min_bore, we still allow min_bore
    # but this will result in a thin rim warning
    bore = max(min_bore, min(target, max_bore))

    # Round to nice values
    if bore < 12:
        # Round to nearest 0.5mm for small bores
        bore = round(bore * 2) / 2
    else:
        # Round to nearest 1mm for larger bores
        bore = round(bore)

    # Ensure at least min_bore
    bore = max(min_bore, bore)

    # Calculate actual rim thickness
    actual_rim = (root_diameter - bore) / 2

    # If rim would be zero or negative, bore is impossible
    if actual_rim <= 0:
        return (None, False)

    # Warning if rim is thin (< 1.5mm)
    has_warning = actual_rim < 1.5

    return (bore, has_warning)
