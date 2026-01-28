"""
JavaScript-Python bridge for Pyodide.

Provides a single, clean entry point for all JS->Python calculator calls.
All inputs are validated via Pydantic models before processing.

Usage from JavaScript:
    pyodide.globals.set('input_json', JSON.stringify(inputs));
    const result = await pyodide.runPythonAsync(`
        from wormgear.calculator.js_bridge import calculate
        calculate(input_json)
    `);
    const design = JSON.parse(result);
"""

import json
from typing import Any, Dict, List, Optional, Union, TypedDict
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValidationMessageDict(TypedDict, total=False):
    """Type for validation message dictionaries sent to JavaScript."""
    severity: str  # "error", "warning", "info"
    code: str  # e.g., "LEAD_ANGLE_LOW"
    message: str
    suggestion: Optional[str]
    standard: Optional[str]  # e.g., "DIN 3975 §7.4"

from ..enums import Hand, WormProfile, WormType
from .core import (
    design_from_module,
    design_from_centre_distance,
    design_from_wheel,
    design_from_envelope,
)
from .validation import validate_design
from .output import to_json, to_markdown, to_summary
from ..core.bore_sizing import calculate_default_bore


# ============================================================================
# Input Models (Pydantic validation for JS inputs)
# ============================================================================

class BoreSettings(BaseModel):
    """Bore configuration from UI.

    Bore types:
    - "none": No bore (solid part)
    - "custom": Custom bore with explicit diameter (required if type is custom)

    Auto-calculation: The UI maps "auto" to "custom" with null diameter.
    The calculator detects this and calculates the bore internally.
    The OUTPUT always has concrete bore_diameter_mm values - the generator
    never sees "auto" or null diameters.
    """
    model_config = ConfigDict(extra='ignore')

    worm_bore_type: str = "none"  # "none" | "custom"
    worm_bore_diameter: Optional[float] = None  # null with custom = auto-calculate
    worm_keyway: str = "none"  # "none" | "DIN6885" | "ddcut"
    wheel_bore_type: str = "none"  # "none" | "custom"
    wheel_bore_diameter: Optional[float] = None  # null with custom = auto-calculate
    wheel_keyway: str = "none"


class ManufacturingSettings(BaseModel):
    """Manufacturing settings from UI."""
    model_config = ConfigDict(extra='ignore')

    virtual_hobbing: bool = False
    hobbing_steps: int = 72
    use_recommended_dims: bool = True
    worm_length_mm: Optional[float] = None
    wheel_width_mm: Optional[float] = None


class CalculatorInputs(BaseModel):
    """
    All inputs from the calculator UI.

    This is the single source of truth for what JavaScript sends to Python.
    """
    model_config = ConfigDict(extra='ignore')

    # Calculation mode
    mode: str = "from-module"  # "from-module" | "from-centre-distance" | "from-wheel" | "envelope"

    # Common parameters
    pressure_angle: float = 20.0
    backlash: float = 0.05
    num_starts: int = 1
    hand: str = "right"
    profile_shift: float = 0.0
    profile: str = "ZA"
    worm_type: str = "cylindrical"
    throat_reduction: float = 0.0
    wheel_throated: bool = False

    # Mode-specific parameters (optional, presence depends on mode)
    module: Optional[float] = None
    ratio: Optional[int] = None
    centre_distance: Optional[float] = None
    worm_od: Optional[float] = None
    wheel_od: Optional[float] = None
    target_lead_angle: Optional[float] = None
    od_as_maximum: bool = False
    use_standard_module: bool = True

    # Nested settings
    bore: BoreSettings = Field(default_factory=BoreSettings)
    manufacturing: ManufacturingSettings = Field(default_factory=ManufacturingSettings)

    @field_validator('hand', mode='before')
    @classmethod
    def normalize_hand(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator('profile', mode='before')
    @classmethod
    def normalize_profile(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator('worm_type', mode='before')
    @classmethod
    def normalize_worm_type(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


# ============================================================================
# Output Models
# ============================================================================

class RecommendedBore(BaseModel):
    """Recommended bore calculation result."""
    model_config = ConfigDict(extra='ignore')

    diameter_mm: Optional[float] = None  # None if gear too small
    has_warning: bool = False  # True if rim is thin
    too_small_for_keyway: bool = False  # True if bore < 6mm (DIN 6885 minimum)


class CalculatorOutput(BaseModel):
    """Output from calculate() - matches what JS expects."""
    model_config = ConfigDict(extra='ignore')

    success: bool
    error: Optional[str] = None

    # Design data (JSON string for JS to parse)
    design_json: Optional[str] = None

    # Display formats
    summary: Optional[str] = None
    markdown: Optional[str] = None

    # Validation
    valid: bool = True
    messages: List[ValidationMessageDict] = Field(default_factory=list)

    # Recommended bore values (calculated by Python, displayed by JS)
    recommended_worm_bore: Optional[RecommendedBore] = None
    recommended_wheel_bore: Optional[RecommendedBore] = None


# ============================================================================
# Main Entry Point
# ============================================================================

def calculate(input_json: str) -> str:
    """
    Single entry point for all calculator operations from JavaScript.

    Args:
        input_json: JSON string with CalculatorInputs structure

    Returns:
        JSON string with CalculatorOutput structure
    """
    try:
        # Parse and validate inputs using Pydantic
        data = json.loads(input_json)
        inputs = CalculatorInputs.model_validate(data)

        # Build function arguments
        kwargs = _build_calculator_kwargs(inputs)

        # Call appropriate design function
        design = _call_design_function(inputs.mode, inputs, kwargs)

        # Auto-default throat reduction for globoid worms using correct geometry
        # The throat pitch radius should equal: center_distance - wheel_pitch_radius
        # So throat_reduction = worm_pitch_radius - throat_pitch_radius
        #                     = worm_pitch_radius - (center_distance - wheel_pitch_radius)
        if inputs.worm_type == 'globoid' and design.worm and design.wheel and design.assembly:
            if not design.worm.throat_reduction_mm or design.worm.throat_reduction_mm <= 0:
                worm_pitch_radius = design.worm.pitch_diameter_mm / 2
                wheel_pitch_radius = design.wheel.pitch_diameter_mm / 2
                center_distance = design.assembly.centre_distance_mm

                # Geometrically correct throat reduction
                throat_reduction = worm_pitch_radius - (center_distance - wheel_pitch_radius)

                # This should be positive for proper globoid geometry
                # If zero or negative, use a small default for visible effect
                if throat_reduction <= 0:
                    throat_reduction = design.worm.pitch_diameter_mm * 0.02  # 2% fallback

                design.worm.throat_reduction_mm = throat_reduction

        # Update manufacturing params from UI settings
        if design.manufacturing:
            design.manufacturing.virtual_hobbing = inputs.manufacturing.virtual_hobbing
            design.manufacturing.hobbing_steps = inputs.manufacturing.hobbing_steps

        # Convert bore settings to dict for validation and output
        bore_dict = inputs.bore.model_dump() if inputs.bore else None

        # Validate the design (pass bore_dict for bore validation before features are added)
        validation = validate_design(design, bore_settings=bore_dict)
        mfg_dict = inputs.manufacturing.model_dump() if inputs.manufacturing else None

        # Handle recommended dimensions - remove from mfg_dict so calculator values aren't overwritten
        if inputs.manufacturing.use_recommended_dims:
            mfg_dict.pop('worm_length_mm', None)
            mfg_dict.pop('wheel_width_mm', None)
        # else: use custom values from user input (already in mfg_dict from model_dump)

        # Remove UI-only fields that shouldn't be in the output JSON
        mfg_dict.pop('use_recommended_dims', None)  # UI toggle, not a manufacturing param

        # Calculate recommended bore values (Python is single source of truth)
        worm_bore_diameter, worm_bore_warning = calculate_default_bore(
            design.worm.pitch_diameter_mm,
            design.worm.root_diameter_mm
        )
        wheel_bore_diameter, wheel_bore_warning = calculate_default_bore(
            design.wheel.pitch_diameter_mm,
            design.wheel.root_diameter_mm
        )

        recommended_worm_bore = RecommendedBore(
            diameter_mm=worm_bore_diameter,
            has_warning=worm_bore_warning,
            too_small_for_keyway=(worm_bore_diameter is not None and worm_bore_diameter < 6.0)
        ) if worm_bore_diameter is not None else RecommendedBore(
            diameter_mm=None,
            has_warning=False,
            too_small_for_keyway=False
        )

        recommended_wheel_bore = RecommendedBore(
            diameter_mm=wheel_bore_diameter,
            has_warning=wheel_bore_warning,
            too_small_for_keyway=(wheel_bore_diameter is not None and wheel_bore_diameter < 6.0)
        ) if wheel_bore_diameter is not None else RecommendedBore(
            diameter_mm=None,
            has_warning=False,
            too_small_for_keyway=False
        )

        # Build output
        output = CalculatorOutput(
            success=True,
            design_json=to_json(design, bore_settings=bore_dict, manufacturing_settings=mfg_dict),
            summary=to_summary(design),
            markdown=to_markdown(design, validation),
            valid=validation.valid,
            messages=[
                {
                    'severity': m.severity.value,
                    'message': m.message,
                    'code': m.code,
                    'suggestion': m.suggestion
                }
                for m in validation.messages
            ],
            recommended_worm_bore=recommended_worm_bore,
            recommended_wheel_bore=recommended_wheel_bore
        )

        return output.model_dump_json()

    except json.JSONDecodeError as e:
        return CalculatorOutput(
            success=False,
            error=f"Invalid JSON: {e}"
        ).model_dump_json()

    except Exception as e:
        return CalculatorOutput(
            success=False,
            error=str(e)
        ).model_dump_json()


def _build_calculator_kwargs(inputs: CalculatorInputs) -> Dict[str, Any]:
    """Build kwargs for calculator functions from validated inputs."""
    kwargs = {
        'pressure_angle': inputs.pressure_angle,
        'backlash': inputs.backlash,
        'num_starts': inputs.num_starts,
        'hand': Hand(inputs.hand),
        'profile': WormProfile(inputs.profile),
        'worm_type': WormType(inputs.worm_type),
        'profile_shift': inputs.profile_shift,
    }

    # Add user-specified throat reduction for globoid worms
    # (auto-default is calculated after design, when we have the pitch diameter)
    if inputs.worm_type == 'globoid':
        if inputs.throat_reduction and inputs.throat_reduction > 0:
            kwargs['throat_reduction'] = inputs.throat_reduction

    # Add wheel throated flag
    if inputs.wheel_throated:
        kwargs['wheel_throated'] = True

    return kwargs


def _call_design_function(mode: str, inputs: CalculatorInputs, kwargs: Dict[str, Any]):
    """Call the appropriate design function based on mode."""
    if mode == 'from-module':
        if inputs.module is None or inputs.ratio is None:
            raise ValueError("module and ratio are required for from-module mode")
        return design_from_module(
            module=inputs.module,
            ratio=inputs.ratio,
            **kwargs
        )
    elif mode == 'from-centre-distance':
        if inputs.centre_distance is None or inputs.ratio is None:
            raise ValueError("centre_distance and ratio are required for from-centre-distance mode")
        return design_from_centre_distance(
            centre_distance=inputs.centre_distance,
            ratio=inputs.ratio,
            **kwargs
        )
    elif mode == 'from-wheel':
        if inputs.wheel_od is None or inputs.ratio is None:
            raise ValueError("wheel_od and ratio are required for from-wheel mode")
        return design_from_wheel(
            wheel_od=inputs.wheel_od,
            ratio=inputs.ratio,
            target_lead_angle=inputs.target_lead_angle or 7.0,
            **kwargs
        )
    elif mode == 'envelope':
        if inputs.worm_od is None or inputs.wheel_od is None or inputs.ratio is None:
            raise ValueError("worm_od, wheel_od, and ratio are required for envelope mode")
        return design_from_envelope(
            worm_od=inputs.worm_od,
            wheel_od=inputs.wheel_od,
            ratio=inputs.ratio,
            od_as_maximum=inputs.od_as_maximum,
            use_standard_module=inputs.use_standard_module,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")


# ============================================================================
# Legacy sanitization functions (kept for backwards compatibility)
# ============================================================================

def sanitize_js_value(value: Any) -> Any:
    """Convert JavaScript value to Python, handling Pyodide edge cases."""
    if value is None:
        return None

    if hasattr(value, '__class__'):
        class_name = str(value.__class__)
        if 'JsNull' in class_name or 'JsUndefined' in class_name:
            return None

    if value == '':
        return None

    if isinstance(value, bool):
        return value

    return value


def sanitize_dict(js_dict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively sanitize a dictionary from JavaScript."""
    if js_dict is None:
        return {}

    result: Dict[str, Any] = {}
    for key, value in js_dict.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized_list = [
                sanitize_dict(v) if isinstance(v, dict) else sanitize_js_value(v)
                for v in value
            ]
            result[key] = sanitized_list
        else:
            result[key] = sanitize_js_value(value)

    return result
