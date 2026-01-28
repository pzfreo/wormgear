"""Type-safe enums for worm gear calculator.

Restored from legacy web/wormcalc/ implementation.
These were incorrectly removed during unified package creation.
"""

from enum import Enum


class Hand(Enum):
    """Thread hand / helix direction"""
    RIGHT = "right"
    LEFT = "left"


class WormProfile(Enum):
    """Worm tooth profile type per DIN 3975"""
    ZA = "ZA"  # Straight trapezoidal flanks - best for CNC machining
    ZK = "ZK"  # Slightly convex flanks - better for 3D printing (FDM layer adhesion)
    ZI = "ZI"  # Involute profile - high precision applications


class WormType(Enum):
    """Worm geometry type"""
    CYLINDRICAL = "cylindrical"  # Standard cylindrical worm
    GLOBOID = "globoid"  # Hourglass-shaped worm for better contact


class BoreType(Enum):
    """Bore configuration type"""
    NONE = "none"  # Solid part, no bore
    CUSTOM = "custom"  # Custom bore diameter specified


class AntiRotation(Enum):
    """Anti-rotation feature type for bores.

    Defines shaft locking features per DIN 6885 and other standards.
    Used in conjunction with BoreType.CUSTOM to specify how the
    bore prevents rotation on the shaft.
    """
    NONE = "none"              # No anti-rotation feature (smooth bore)
    DIN6885 = "DIN6885"        # Standard keyway per DIN 6885/ISO 6885
    DDCUT = "ddcut"            # DD-cut (double-D flat) for small shafts
