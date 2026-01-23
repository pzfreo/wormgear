"""
JSON input/output for worm gear parameters.

Loads design parameters from wormgearcalc (Tool 1) JSON output.
Supports extended JSON format with manufacturing features (bore, keyway, set screws, hubs).
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Union, Dict, Any


@dataclass
class WormParams:
    """Worm parameters from calculator."""
    module_mm: float
    num_starts: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    lead_mm: float
    lead_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    thread_thickness_mm: float
    hand: str  # "RIGHT" or "LEFT"
    profile_shift: float = 0.0


@dataclass
class WheelParams:
    """Wheel parameters from calculator."""
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


@dataclass
class AssemblyParams:
    """Assembly parameters from calculator."""
    centre_distance_mm: float
    pressure_angle_deg: float
    backlash_mm: float
    hand: str
    ratio: int
    efficiency_percent: Optional[float] = None
    self_locking: Optional[bool] = None


@dataclass
class ManufacturingFeatures:
    """Manufacturing features for a gear part (worm or wheel)."""
    bore_diameter: Optional[float] = None
    keyway_width: Optional[float] = None
    keyway_depth: Optional[float] = None
    set_screw_size: Optional[str] = None
    set_screw_count: Optional[int] = None
    # Hub features (wheel only)
    hub_type: Optional[str] = None
    hub_length: Optional[float] = None
    flange_diameter: Optional[float] = None
    flange_thickness: Optional[float] = None
    flange_bolts: Optional[int] = None
    bolt_diameter: Optional[float] = None


@dataclass
class ManufacturingParams:
    """Manufacturing parameters for worm and wheel."""
    worm_length: float = 40.0
    wheel_width: Optional[float] = None
    wheel_throated: bool = False
    worm_features: Optional[ManufacturingFeatures] = None
    wheel_features: Optional[ManufacturingFeatures] = None


@dataclass
class WormGearDesign:
    """Complete worm gear design from calculator."""
    worm: WormParams
    wheel: WheelParams
    assembly: AssemblyParams
    manufacturing: Optional[ManufacturingParams] = None


def load_design_json(filepath: Union[str, Path]) -> WormGearDesign:
    """
    Load worm gear design from calculator JSON export.

    Args:
        filepath: Path to JSON file from wormgearcalc

    Returns:
        WormGearDesign with all parameters

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid or missing required fields
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

    # Parse worm parameters
    # Note: 'hand' may be in worm or assembly section depending on Tool 1 version
    worm_data = data['worm']
    asm_data = data['assembly']
    worm_hand = worm_data.get('hand', asm_data.get('hand', 'RIGHT'))

    worm = WormParams(
        module_mm=worm_data['module_mm'],
        num_starts=worm_data['num_starts'],
        pitch_diameter_mm=worm_data['pitch_diameter_mm'],
        tip_diameter_mm=worm_data['tip_diameter_mm'],
        root_diameter_mm=worm_data['root_diameter_mm'],
        lead_mm=worm_data['lead_mm'],
        lead_angle_deg=worm_data['lead_angle_deg'],
        addendum_mm=worm_data['addendum_mm'],
        dedendum_mm=worm_data['dedendum_mm'],
        thread_thickness_mm=worm_data['thread_thickness_mm'],
        hand=worm_hand,
        profile_shift=worm_data.get('profile_shift', 0.0)
    )

    # Parse wheel parameters
    wheel_data = data['wheel']
    wheel = WheelParams(
        module_mm=wheel_data['module_mm'],
        num_teeth=wheel_data['num_teeth'],
        pitch_diameter_mm=wheel_data['pitch_diameter_mm'],
        tip_diameter_mm=wheel_data['tip_diameter_mm'],
        root_diameter_mm=wheel_data['root_diameter_mm'],
        throat_diameter_mm=wheel_data['throat_diameter_mm'],
        helix_angle_deg=wheel_data['helix_angle_deg'],
        addendum_mm=wheel_data['addendum_mm'],
        dedendum_mm=wheel_data['dedendum_mm'],
        profile_shift=wheel_data.get('profile_shift', 0.0)
    )

    # Parse assembly parameters (asm_data already extracted above)
    assembly = AssemblyParams(
        centre_distance_mm=asm_data['centre_distance_mm'],
        pressure_angle_deg=asm_data['pressure_angle_deg'],
        backlash_mm=asm_data['backlash_mm'],
        hand=asm_data.get('hand', worm_hand),
        ratio=asm_data['ratio'],
        efficiency_percent=asm_data.get('efficiency_percent'),
        self_locking=asm_data.get('self_locking')
    )

    # Parse optional manufacturing parameters (if present)
    manufacturing = None
    if 'manufacturing' in data:
        mfg_data = data['manufacturing']

        # Parse worm features
        worm_features = None
        if 'worm_features' in mfg_data:
            wf = mfg_data['worm_features']
            worm_features = ManufacturingFeatures(
                bore_diameter=wf.get('bore_diameter'),
                keyway_width=wf.get('keyway_width'),
                keyway_depth=wf.get('keyway_depth'),
                set_screw_size=wf.get('set_screw_size'),
                set_screw_count=wf.get('set_screw_count')
            )

        # Parse wheel features
        wheel_features = None
        if 'wheel_features' in mfg_data:
            wf = mfg_data['wheel_features']
            wheel_features = ManufacturingFeatures(
                bore_diameter=wf.get('bore_diameter'),
                keyway_width=wf.get('keyway_width'),
                keyway_depth=wf.get('keyway_depth'),
                set_screw_size=wf.get('set_screw_size'),
                set_screw_count=wf.get('set_screw_count'),
                hub_type=wf.get('hub_type'),
                hub_length=wf.get('hub_length'),
                flange_diameter=wf.get('flange_diameter'),
                flange_thickness=wf.get('flange_thickness'),
                flange_bolts=wf.get('flange_bolts'),
                bolt_diameter=wf.get('bolt_diameter')
            )

        manufacturing = ManufacturingParams(
            worm_length=mfg_data.get('worm_length', 40.0),
            wheel_width=mfg_data.get('wheel_width'),
            wheel_throated=mfg_data.get('wheel_throated', False),
            worm_features=worm_features,
            wheel_features=wheel_features
        )

    return WormGearDesign(worm=worm, wheel=wheel, assembly=assembly, manufacturing=manufacturing)


def save_design_json(design: WormGearDesign, filepath: Union[str, Path]) -> None:
    """
    Save complete worm gear design to JSON file.

    Exports both calculator parameters and manufacturing features to JSON.
    This format can be loaded back to reproduce the exact same part.

    Args:
        design: Complete worm gear design including manufacturing params
        filepath: Path to save JSON file

    Raises:
        IOError: If file cannot be written
    """
    filepath = Path(filepath)

    # Convert dataclasses to dict
    # Note: asdict creates nested dicts but includes None values
    data = {
        'worm': {k: v for k, v in asdict(design.worm).items() if v is not None},
        'wheel': {k: v for k, v in asdict(design.wheel).items() if v is not None},
        'assembly': {k: v for k, v in asdict(design.assembly).items() if v is not None}
    }

    # Add manufacturing section if present
    if design.manufacturing is not None:
        mfg_dict: Dict[str, Any] = {
            'worm_length': design.manufacturing.worm_length,
            'wheel_throated': design.manufacturing.wheel_throated
        }

        if design.manufacturing.wheel_width is not None:
            mfg_dict['wheel_width'] = design.manufacturing.wheel_width

        # Add worm features if present
        if design.manufacturing.worm_features is not None:
            wf = design.manufacturing.worm_features
            wf_dict = {k: v for k, v in asdict(wf).items() if v is not None and not k.startswith('hub')}
            if wf_dict:
                mfg_dict['worm_features'] = wf_dict

        # Add wheel features if present
        if design.manufacturing.wheel_features is not None:
            wf = design.manufacturing.wheel_features
            wf_dict = {k: v for k, v in asdict(wf).items() if v is not None}
            if wf_dict:
                mfg_dict['wheel_features'] = wf_dict

        data['manufacturing'] = mfg_dict

    # Write JSON with nice formatting
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def create_manufacturing_features_from_parts(
    bore_diameter: Optional[float] = None,
    keyway_width: Optional[float] = None,
    keyway_depth: Optional[float] = None,
    set_screw_size: Optional[str] = None,
    set_screw_count: Optional[int] = None,
    hub_type: Optional[str] = None,
    hub_length: Optional[float] = None,
    flange_diameter: Optional[float] = None,
    flange_thickness: Optional[float] = None,
    flange_bolts: Optional[int] = None,
    bolt_diameter: Optional[float] = None
) -> ManufacturingFeatures:
    """
    Helper to create ManufacturingFeatures from individual parameters.

    Args:
        bore_diameter: Bore diameter in mm
        keyway_width: Keyway width in mm
        keyway_depth: Keyway depth in mm
        set_screw_size: Set screw size (e.g., "M4")
        set_screw_count: Number of set screws (1-3)
        hub_type: Hub type ("flush", "extended", "flanged")
        hub_length: Hub extension length in mm
        flange_diameter: Flange diameter in mm
        flange_thickness: Flange thickness in mm
        flange_bolts: Number of bolt holes
        bolt_diameter: Bolt hole diameter in mm

    Returns:
        ManufacturingFeatures object
    """
    return ManufacturingFeatures(
        bore_diameter=bore_diameter,
        keyway_width=keyway_width,
        keyway_depth=keyway_depth,
        set_screw_size=set_screw_size,
        set_screw_count=set_screw_count,
        hub_type=hub_type,
        hub_length=hub_length,
        flange_diameter=flange_diameter,
        flange_thickness=flange_thickness,
        flange_bolts=flange_bolts,
        bolt_diameter=bolt_diameter
    )
