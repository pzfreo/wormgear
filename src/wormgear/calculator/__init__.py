"""
Wormgear Calculator - Worm gear parameter calculation.

This module provides engineering calculation functions to design worm gear pairs
from user constraints. Ported from wormgearcalc.

Example:
    >>> from wormgear.calculator import design_from_module, validate_design
    >>>
    >>> # Calculate design from standard module and ratio
    >>> design = design_from_module(
    ...     module=2.0,
    ...     ratio=30,
    ...     pressure_angle=20.0
    ... )
    >>>
    >>> # Validate design
    >>> validation = validate_design(design)
    >>> if validation.valid:
    ...     print(f"Valid design!")
    >>> for warning in validation.warnings:
    ...     print(f"Warning: {warning.message}")
"""

# To be ported from wormgearcalc
# - solver.py - design_from_module(), design_from_envelope(), etc.
# - constraints.py - STANDARD_MODULES, DIN 3975 constraints
# - validation.py - validate_design(), validation rules
# - recommendations.py - calculate lengths, widths
# - globoid.py - globoid-specific calculations

__all__ = [
    # Will be populated as we port from wormgearcalc
]
