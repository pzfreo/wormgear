"""
Worm gear calculations module.

This module contains pure mathematical calculations for worm gear design.
These functions can be imported by the calculator (wormgearcalc) to provide
a single source of truth for all worm gear mathematics.

NO build123d dependency - pure calculations only.
"""

from .globoid import (
    validate_clearance,
    recommend_wheel_width,
    recommend_worm_length,
    validate_throat_reduction,
    calculate_throat_geometry,
)

from .schema import (
    SCHEMA_VERSION,
    validate_json_schema,
    upgrade_schema,
)

__all__ = [
    # Globoid calculations
    "validate_clearance",
    "recommend_wheel_width",
    "recommend_worm_length",
    "validate_throat_reduction",
    "calculate_throat_geometry",

    # Schema
    "SCHEMA_VERSION",
    "validate_json_schema",
    "upgrade_schema",
]
