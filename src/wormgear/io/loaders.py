"""
JSON input/output for worm gear parameters.

Loads design parameters from wormgearcalc (Tool 1) JSON output.
Supports schema v1.0 with separate features section.

Uses Pydantic for automatic validation and enum coercion.
"""

import json
from math import pi
from pathlib import Path
from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field, validator, root_validator

from ..enums import Hand, WormType, WormProfile


# Check Pydantic version for API compatibility
try:
    from pydantic import __version__ as PYDANTIC_VERSION
    PYDANTIC_V2 = int(PYDANTIC_VERSION.split('.')[0]) >= 2
except:
    PYDANTIC_V2 = False


class SetScrewSpec(BaseModel):
    """Set screw specification."""
    size: str  # e.g., "M2", "M3", "M4"
    count: int = 1  # Number of set screws (1-3)

    class Config:
        extra = 'ignore'


class HubSpec(BaseModel):
    """Hub specification (wheel only)."""
    type: str = "flush"  # "flush", "extended", "flanged"
    length_mm: Optional[float] = None  # For extended/flanged
    flange_diameter_mm: Optional[float] = None  # For flanged only
    flange_thickness_mm: Optional[float] = None  # For flanged only
    bolt_holes: Optional[int] = None  # For flanged only
    bolt_diameter_mm: Optional[float] = None  # For flanged only

    class Config:
        extra = 'ignore'


class WormFeatures(BaseModel):
    """Manufacturing features for worm."""
    bore_diameter_mm: Optional[float] = None
    anti_rotation: Optional[str] = None  # "none" | "DIN6885" | "ddcut"
    ddcut_depth_percent: float = 15.0  # Only used if anti_rotation is "ddcut"
    set_screw: Optional[SetScrewSpec] = None

    class Config:
        extra = 'ignore'


class WheelFeatures(BaseModel):
    """Manufacturing features for wheel."""
    bore_diameter_mm: Optional[float] = None
    anti_rotation: Optional[str] = None  # "none" | "DIN6885" | "ddcut"
    ddcut_depth_percent: float = 15.0  # Only used if anti_rotation is "ddcut"
    set_screw: Optional[SetScrewSpec] = None
    hub: Optional[HubSpec] = None

    class Config:
        extra = 'ignore'


class Features(BaseModel):
    """Manufacturing features for worm and wheel."""
    worm: Optional[WormFeatures] = None
    wheel: Optional[WheelFeatures] = None

    class Config:
        extra = 'ignore'


class ManufacturingParams(BaseModel):
    """Manufacturing/generation parameters."""
    profile: WormProfile = WormProfile.ZA
    virtual_hobbing: bool = False
    hobbing_steps: int = 18
    throated_wheel: bool = False
    sections_per_turn: int = 36
    worm_length_mm: Optional[float] = None
    wheel_width_mm: Optional[float] = None

    @validator('profile', pre=True)
    def coerce_profile(cls, v):
        if isinstance(v, str):
            return WormProfile(v.upper())
        return v

    class Config:
        extra = 'ignore'
        use_enum_values = False  # Keep as enum internally


class WormParams(BaseModel):
    """Worm dimensional parameters from calculator."""
    module_mm: float
    num_starts: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    lead_mm: float
    axial_pitch_mm: Optional[float] = None  # Auto-calculated if missing
    lead_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    thread_thickness_mm: float
    hand: Hand
    profile_shift: float = 0.0
    type: Optional[WormType] = None
    throat_reduction_mm: Optional[float] = None
    throat_curvature_radius_mm: Optional[float] = None
    length_mm: Optional[float] = None

    @validator('hand', pre=True)
    def coerce_hand(cls, v):
        if isinstance(v, str):
            return Hand(v.lower())
        return v

    @validator('type', pre=True)
    def coerce_type(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return WormType(v.lower())
        return v

    @validator('axial_pitch_mm', always=True)
    def calc_axial_pitch(cls, v, values):
        if v is None and 'module_mm' in values:
            return values['module_mm'] * pi
        return v

    class Config:
        extra = 'ignore'
        use_enum_values = False


class WheelParams(BaseModel):
    """Wheel dimensional parameters from calculator."""
    module_mm: float
    num_teeth: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    throat_diameter_mm: float
    helix_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    profile_shift: float = 0.0
    width_mm: Optional[float] = None

    class Config:
        extra = 'ignore'


class AssemblyParams(BaseModel):
    """Assembly parameters from calculator."""
    centre_distance_mm: float
    pressure_angle_deg: float
    backlash_mm: float
    hand: Hand
    ratio: int
    efficiency_percent: Optional[float] = None
    self_locking: Optional[bool] = None

    @validator('hand', pre=True)
    def coerce_hand(cls, v):
        if isinstance(v, str):
            return Hand(v.lower())
        return v

    class Config:
        extra = 'ignore'
        use_enum_values = False


class WormGearDesign(BaseModel):
    """Complete worm gear design from calculator."""
    worm: WormParams
    wheel: WheelParams
    assembly: AssemblyParams
    features: Optional[Features] = None
    manufacturing: Optional[ManufacturingParams] = None

    class Config:
        extra = 'ignore'


# Legacy dataclass for backward compatibility
class ManufacturingFeatures(BaseModel):
    """Manufacturing features for a gear part - LEGACY."""
    bore_diameter: Optional[float] = None
    keyway_width: Optional[float] = None
    keyway_depth: Optional[float] = None
    set_screw_size: Optional[str] = None
    set_screw_count: Optional[int] = None
    hub_type: Optional[str] = None
    hub_length: Optional[float] = None
    flange_diameter: Optional[float] = None
    flange_thickness: Optional[float] = None
    flange_bolts: Optional[int] = None
    bolt_diameter: Optional[float] = None

    class Config:
        extra = 'ignore'


def _parse_obj(model_class, data: dict):
    """Parse dict to model, handling both Pydantic v1 and v2."""
    if PYDANTIC_V2:
        return model_class.model_validate(data)
    else:
        return model_class.parse_obj(data)


def _to_dict(model) -> dict:
    """Convert model to dict, handling both Pydantic v1 and v2."""
    if PYDANTIC_V2:
        return model.model_dump(exclude_none=True)
    else:
        return model.dict(exclude_none=True)


def load_design_json(filepath: Union[str, Path]) -> WormGearDesign:
    """
    Load worm gear design from calculator JSON export.

    Uses Pydantic for automatic validation and enum coercion.

    Args:
        filepath: Path to JSON file from wormgearcalc

    Returns:
        WormGearDesign with all parameters

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If JSON is invalid or missing required fields
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Design file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Check for 'design' wrapper (some exports have this)
    if 'design' in data:
        data = data['design']

    # Validate required sections
    if 'worm' not in data or 'wheel' not in data or 'assembly' not in data:
        raise ValueError(
            "Invalid design JSON - must contain 'worm', 'wheel', and 'assembly' sections"
        )

    # Handle 'hand' that may be in worm or assembly section
    worm_data = data['worm']
    asm_data = data['assembly']
    if 'hand' not in worm_data and 'hand' in asm_data:
        worm_data['hand'] = asm_data['hand']
    if 'hand' not in asm_data and 'hand' in worm_data:
        asm_data['hand'] = worm_data['hand']

    # Pydantic does all the heavy lifting here
    return _parse_obj(WormGearDesign, data)


def save_design_json(design: WormGearDesign, filepath: Union[str, Path]) -> None:
    """
    Save complete worm gear design to JSON file using schema v1.0 format.

    Args:
        design: Complete worm gear design
        filepath: Path to save JSON file
    """
    filepath = Path(filepath)

    # Convert to dict, handling enums
    data = _to_dict(design)

    # Add schema version
    data['schema_version'] = '1.0'

    # Convert enums to their values for JSON
    def convert_enums(obj):
        if isinstance(obj, dict):
            return {k: convert_enums(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_enums(v) for v in obj]
        elif hasattr(obj, 'value'):  # Enum
            return obj.value
        return obj

    data = convert_enums(data)

    # Write JSON with nice formatting
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
