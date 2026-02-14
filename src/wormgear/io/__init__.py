"""
Wormgear IO - JSON schema, loaders, and exporters.

This module handles JSON serialization/deserialization and output generation.

Example:
    >>> from wormgear.io import load_design_json, save_design_json
    >>> from wormgear.calculator import design_from_module
    >>>
    >>> # Calculate design
    >>> design = design_from_module(module=2.0, ratio=30)
    >>>
    >>> # Save to JSON
    >>> save_design_json(design, "design.json")
    >>>
    >>> # Load back
    >>> loaded = load_design_json("design.json")
"""

# Import from loaders module
from .loaders import (
    load_design_json,
    save_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign,
    Features,
    WormFeatures,
    WheelFeatures,
    SetScrewSpec,
    HubSpec,
    ManufacturingParams,
    ManufacturingFeatures,  # Legacy
    # Mesh alignment
    MeshAlignment,
    WormPosition,
    # Measured geometry
    MeasuredGeometry,
    MeasurementPoint,
)

# Import from package module (shared export/packaging)
# Requires build123d — not available in Pyodide calculator-only mode
try:
    from .package import (
        PackageFiles,
        generate_package,
        save_package_to_dir,
        create_package_zip,
    )
except ImportError:
    pass

# Import from schema module
from .schema import (
    SCHEMA_VERSION,
    get_schema_v1,
    validate_json_schema,
    create_example_schema_v1,
)

__all__ = [
    # Loaders
    "load_design_json",
    "save_design_json",

    # Parameters
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "WormGearDesign",
    "Features",
    "WormFeatures",
    "WheelFeatures",
    "SetScrewSpec",
    "HubSpec",
    "ManufacturingParams",
    "ManufacturingFeatures",  # Legacy

    # Mesh alignment
    "MeshAlignment",
    "WormPosition",

    # Measured geometry
    "MeasuredGeometry",
    "MeasurementPoint",

    # Package export
    "PackageFiles",
    "generate_package",
    "save_package_to_dir",
    "create_package_zip",

    # Schema
    "SCHEMA_VERSION",
    "get_schema_v1",
    "validate_json_schema",
    "create_example_schema_v1",
]
