#!/usr/bin/env python3
"""
Generate JSON Schemas from Pydantic models.

This is the first step in the schema-first workflow:
1. Pydantic models (source of truth) -> JSON Schema
2. JSON Schema -> TypeScript types (via generate_types.sh)

Usage:
    python scripts/generate_schemas.py
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wormgear.io.loaders import (
    WormGearDesign,
    WormParams,
    WheelParams,
    AssemblyParams,
    ManufacturingParams,
    Features,
    WormFeatures,
    WheelFeatures,
    SetScrewSpec,
    HubSpec,
)
from wormgear.enums import Hand, WormProfile, WormType

# Check Pydantic version
try:
    from pydantic import __version__ as PYDANTIC_VERSION
    PYDANTIC_V2 = int(PYDANTIC_VERSION.split('.')[0]) >= 2
except:
    PYDANTIC_V2 = False


def get_model_schema(model_class) -> dict:
    """Get JSON schema from a Pydantic model.

    Uses by_alias=False to use field names (not aliases) in the schema.
    This ensures the schema matches what model_dump() produces by default.
    """
    if PYDANTIC_V2:
        return model_class.model_json_schema(by_alias=False)
    else:
        return model_class.schema()


def main():
    output_dir = Path(__file__).parent.parent / "schemas"
    output_dir.mkdir(exist_ok=True)

    print("Generating JSON schemas from Pydantic models...")
    print(f"  Pydantic version: {PYDANTIC_VERSION} ({'v2' if PYDANTIC_V2 else 'v1'})")

    # Generate main design schema
    design_schema = get_model_schema(WormGearDesign)
    design_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    design_schema["$id"] = "https://wormgear.studio/schemas/wormgear-design-v2.0.json"
    design_schema["title"] = "WormGearDesign"
    design_schema["description"] = "Complete worm gear design output from calculator"

    design_file = output_dir / "wormgear-design-v2.0.json"
    with open(design_file, "w") as f:
        json.dump(design_schema, f, indent=2)
    print(f"  Generated: {design_file}")

    # Generate individual component schemas for reference
    components = {
        "worm-params": WormParams,
        "wheel-params": WheelParams,
        "assembly-params": AssemblyParams,
        "manufacturing-params": ManufacturingParams,
        "features": Features,
    }

    for name, model in components.items():
        schema = get_model_schema(model)
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://wormgear.studio/schemas/{name}-v2.0.json"

        schema_file = output_dir / f"{name}-v2.0.json"
        with open(schema_file, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"  Generated: {schema_file}")

    # Generate enums schema
    enums_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://wormgear.studio/schemas/enums-v2.0.json",
        "title": "WormgearEnums",
        "description": "Enum definitions for wormgear types",
        "definitions": {
            "Hand": {
                "type": "string",
                "enum": [e.value for e in Hand],
                "description": "Thread/gear hand direction"
            },
            "WormProfile": {
                "type": "string",
                "enum": [e.value for e in WormProfile],
                "description": "Tooth profile per DIN 3975"
            },
            "WormType": {
                "type": "string",
                "enum": [e.value for e in WormType],
                "description": "Worm geometry type"
            }
        }
    }

    enums_file = output_dir / "enums-v2.0.json"
    with open(enums_file, "w") as f:
        json.dump(enums_schema, f, indent=2)
    print(f"  Generated: {enums_file}")

    print(f"\nAll schemas written to: {output_dir}/")
    print("Next step: bash scripts/generate_types.sh")


if __name__ == "__main__":
    main()
