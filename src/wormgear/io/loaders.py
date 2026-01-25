"""
JSON input/output for worm gear parameters.

Loads design parameters from wormgearcalc (Tool 1) JSON output.
Supports schema v1.0 with separate features section (Option B).
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Union, Dict, Any


@dataclass
class WormParams:
    """Worm dimensional parameters from calculator."""
    # Core dimensions (always required)
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

    # Worm type (cylindrical or globoid)
    type: Optional[str] = None  # "cylindrical" or "globoid"

    # Globoid-specific parameters (only if type="globoid")
    throat_reduction_mm: Optional[float] = None
    throat_curvature_radius_mm: Optional[float] = None

    # Geometry override (if None, CLI provides default)
    length_mm: Optional[float] = None


@dataclass
class WheelParams:
    """Wheel dimensional parameters from calculator."""
    # Core dimensions (always required)
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

    # Geometry override (if None, CLI auto-calculates)
    width_mm: Optional[float] = None


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
class SetScrewSpec:
    """Set screw specification."""
    size: str  # e.g., "M2", "M3", "M4"
    count: int = 1  # Number of set screws (1-3)


@dataclass
class HubSpec:
    """Hub specification (wheel only)."""
    type: str = "flush"  # "flush", "extended", "flanged"
    length_mm: Optional[float] = None  # For extended/flanged
    flange_diameter_mm: Optional[float] = None  # For flanged only
    flange_thickness_mm: Optional[float] = None  # For flanged only
    bolt_holes: Optional[int] = None  # For flanged only
    bolt_diameter_mm: Optional[float] = None  # For flanged only


@dataclass
class WormFeatures:
    """Manufacturing features for worm."""
    bore_diameter_mm: Optional[float] = None
    anti_rotation: Optional[str] = None  # "none" | "DIN6885" | "ddcut"
    ddcut_depth_percent: float = 15.0  # Only used if anti_rotation is "ddcut"
    set_screw: Optional[SetScrewSpec] = None


@dataclass
class WheelFeatures:
    """Manufacturing features for wheel."""
    bore_diameter_mm: Optional[float] = None
    anti_rotation: Optional[str] = None  # "none" | "DIN6885" | "ddcut"
    ddcut_depth_percent: float = 15.0  # Only used if anti_rotation is "ddcut"
    set_screw: Optional[SetScrewSpec] = None
    hub: Optional[HubSpec] = None


@dataclass
class Features:
    """Manufacturing features for worm and wheel."""
    worm: Optional[WormFeatures] = None
    wheel: Optional[WheelFeatures] = None


@dataclass
class ManufacturingParams:
    """Manufacturing/generation parameters."""
    profile: str = "ZA"  # Tooth profile: "ZA" (straight), "ZK" (circular arc), "ZI" (involute)
    virtual_hobbing: bool = False  # Use virtual hobbing simulation for wheel
    hobbing_steps: int = 18  # Number of steps for virtual hobbing (if enabled)
    throated_wheel: bool = False  # True for throated/hobbed wheel style
    sections_per_turn: int = 36  # Loft sections per helix turn (smoothness)


@dataclass
class WormGearDesign:
    """Complete worm gear design from calculator."""
    worm: WormParams
    wheel: WheelParams
    assembly: AssemblyParams
    features: Optional[Features] = None
    manufacturing: Optional[ManufacturingParams] = None


# Legacy dataclasses for backward compatibility with old CLI save-json format
@dataclass
class ManufacturingFeatures:
    """Manufacturing features for a gear part (worm or wheel) - LEGACY."""
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


def load_design_json(filepath: Union[str, Path]) -> WormGearDesign:
    """
    Load worm gear design from calculator JSON export.

    Supports both:
    - Schema v1.0 with separate features section (new)
    - Legacy format with features in worm/wheel params (old)

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
        profile_shift=worm_data.get('profile_shift', 0.0),
        # Schema v1.0 fields (simplified)
        type=worm_data.get('type'),
        throat_reduction_mm=worm_data.get('throat_reduction_mm'),
        throat_curvature_radius_mm=worm_data.get('throat_curvature_radius_mm'),
        length_mm=worm_data.get('length_mm')
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
        profile_shift=wheel_data.get('profile_shift', 0.0),
        # Schema v1.0 field (simplified)
        width_mm=wheel_data.get('width_mm')
    )

    # Parse assembly parameters
    assembly = AssemblyParams(
        centre_distance_mm=asm_data['centre_distance_mm'],
        pressure_angle_deg=asm_data['pressure_angle_deg'],
        backlash_mm=asm_data['backlash_mm'],
        hand=asm_data.get('hand', worm_hand),
        ratio=asm_data['ratio'],
        efficiency_percent=asm_data.get('efficiency_percent'),
        self_locking=asm_data.get('self_locking')
    )

    # Parse features section (schema v1.0 Option B)
    features = None
    if 'features' in data:
        features_data = data['features']

        # Parse worm features
        worm_features = None
        if 'worm' in features_data:
            wf_data = features_data['worm']
            worm_set_screw = None
            if 'set_screw' in wf_data and wf_data['set_screw']:
                ss_data = wf_data['set_screw']
                worm_set_screw = SetScrewSpec(
                    size=ss_data['size'],
                    count=ss_data.get('count', 1)
                )

            worm_features = WormFeatures(
                bore_diameter_mm=wf_data.get('bore_diameter_mm'),
                anti_rotation=wf_data.get('anti_rotation'),
                ddcut_depth_percent=wf_data.get('ddcut_depth_percent', 15.0),
                set_screw=worm_set_screw
            )

        # Parse wheel features
        wheel_features = None
        if 'wheel' in features_data:
            wf_data = features_data['wheel']
            wheel_set_screw = None
            if 'set_screw' in wf_data and wf_data['set_screw']:
                ss_data = wf_data['set_screw']
                wheel_set_screw = SetScrewSpec(
                    size=ss_data['size'],
                    count=ss_data.get('count', 1)
                )

            wheel_hub = None
            if 'hub' in wf_data and wf_data['hub']:
                hub_data = wf_data['hub']
                wheel_hub = HubSpec(
                    type=hub_data.get('type', 'flush'),
                    length_mm=hub_data.get('length_mm'),
                    flange_diameter_mm=hub_data.get('flange_diameter_mm'),
                    flange_thickness_mm=hub_data.get('flange_thickness_mm'),
                    bolt_holes=hub_data.get('bolt_holes'),
                    bolt_diameter_mm=hub_data.get('bolt_diameter_mm')
                )

            wheel_features = WheelFeatures(
                bore_diameter_mm=wf_data.get('bore_diameter_mm'),
                anti_rotation=wf_data.get('anti_rotation'),
                ddcut_depth_percent=wf_data.get('ddcut_depth_percent', 15.0),
                set_screw=wheel_set_screw,
                hub=wheel_hub
            )

        features = Features(worm=worm_features, wheel=wheel_features)

    # Parse manufacturing parameters
    manufacturing = None
    if 'manufacturing' in data:
        mfg_data = data['manufacturing']
        manufacturing = ManufacturingParams(
            profile=mfg_data.get('profile', 'ZA'),
            virtual_hobbing=mfg_data.get('virtual_hobbing', False),
            hobbing_steps=mfg_data.get('hobbing_steps', 18),
            throated_wheel=mfg_data.get('throated_wheel', False),
            sections_per_turn=mfg_data.get('sections_per_turn', 36)
        )

    return WormGearDesign(
        worm=worm,
        wheel=wheel,
        assembly=assembly,
        features=features,
        manufacturing=manufacturing
    )


def save_design_json(design: WormGearDesign, filepath: Union[str, Path]) -> None:
    """
    Save complete worm gear design to JSON file using schema v1.0 format.

    Exports both calculator parameters and manufacturing features to JSON.
    This format can be loaded back to reproduce the exact same part.

    Args:
        design: Complete worm gear design including features and manufacturing params
        filepath: Path to save JSON file

    Raises:
        IOError: If file cannot be written
    """
    filepath = Path(filepath)

    # Convert dataclasses to dict (exclude None values for cleaner JSON)
    data: Dict[str, Any] = {
        'schema_version': '1.0',
        'worm': {k: v for k, v in asdict(design.worm).items() if v is not None},
        'wheel': {k: v for k, v in asdict(design.wheel).items() if v is not None},
        'assembly': {k: v for k, v in asdict(design.assembly).items() if v is not None}
    }

    # Add features section if present
    if design.features is not None:
        features_dict: Dict[str, Any] = {}

        if design.features.worm is not None:
            worm_feat = design.features.worm
            worm_dict: Dict[str, Any] = {}
            if worm_feat.bore_diameter_mm is not None:
                worm_dict['bore_diameter_mm'] = worm_feat.bore_diameter_mm
            if worm_feat.anti_rotation is not None:
                worm_dict['anti_rotation'] = worm_feat.anti_rotation
            if worm_feat.anti_rotation == 'ddcut':
                worm_dict['ddcut_depth_percent'] = worm_feat.ddcut_depth_percent
            if worm_feat.set_screw is not None:
                worm_dict['set_screw'] = asdict(worm_feat.set_screw)
            if worm_dict:
                features_dict['worm'] = worm_dict

        if design.features.wheel is not None:
            wheel_feat = design.features.wheel
            wheel_dict: Dict[str, Any] = {}
            if wheel_feat.bore_diameter_mm is not None:
                wheel_dict['bore_diameter_mm'] = wheel_feat.bore_diameter_mm
            if wheel_feat.anti_rotation is not None:
                wheel_dict['anti_rotation'] = wheel_feat.anti_rotation
            if wheel_feat.anti_rotation == 'ddcut':
                wheel_dict['ddcut_depth_percent'] = wheel_feat.ddcut_depth_percent
            if wheel_feat.set_screw is not None:
                wheel_dict['set_screw'] = asdict(wheel_feat.set_screw)
            if wheel_feat.hub is not None:
                hub_dict = {k: v for k, v in asdict(wheel_feat.hub).items() if v is not None}
                if hub_dict:
                    wheel_dict['hub'] = hub_dict
            if wheel_dict:
                features_dict['wheel'] = wheel_dict

        if features_dict:
            data['features'] = features_dict

    # Add manufacturing section if present
    if design.manufacturing is not None:
        mfg_dict = {k: v for k, v in asdict(design.manufacturing).items() if v is not None}
        if mfg_dict:
            data['manufacturing'] = mfg_dict

    # Write JSON with nice formatting
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
