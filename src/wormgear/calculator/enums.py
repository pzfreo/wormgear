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
