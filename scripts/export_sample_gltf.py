#!/usr/bin/env python3
"""Export sample worm+wheel as STL for Three.js animation prototype.

Generates a default worm+wheel pair, calculates optimal mesh alignment,
and exports the parts as .stl files with positioning metadata.

Usage:
    python scripts/export_sample_gltf.py
"""

import json
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wormgear.calculator.core import design_from_module
from wormgear.core.worm import WormGeometry
from wormgear.core.wheel import WheelGeometry
from wormgear.core.features import BoreFeature, calculate_default_bore
from wormgear.core.mesh_alignment import find_optimal_mesh_rotation


def main():
    output_dir = Path(__file__).parent.parent / "web" / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate a standard design
    print("Calculating design (module=2.0, ratio=30)...")
    design = design_from_module(module=2.0, ratio=30)

    # Build worm with bore
    print("Building worm geometry...")
    worm_bore_dia, _ = calculate_default_bore(
        design.worm.pitch_diameter_mm, design.worm.root_diameter_mm
    )
    worm_geo = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=40.0,
        sections_per_turn=36,
        bore=BoreFeature(diameter=worm_bore_dia) if worm_bore_dia else None,
    )
    worm = worm_geo.build()

    # Build wheel with bore
    print("Building wheel geometry...")
    wheel_bore_dia, _ = calculate_default_bore(
        design.wheel.pitch_diameter_mm, design.wheel.root_diameter_mm
    )
    wheel_geo = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        bore=BoreFeature(diameter=wheel_bore_dia) if wheel_bore_dia else None,
    )
    wheel = wheel_geo.build()

    # Calculate optimal mesh alignment (reuses mesh_alignment.py)
    print("Calculating mesh alignment...")
    mesh_result = find_optimal_mesh_rotation(
        wheel=wheel,
        worm=worm,
        centre_distance_mm=design.assembly.centre_distance_mm,
        num_teeth=design.wheel.num_teeth,
    )
    print(f"  Optimal rotation: {mesh_result.optimal_rotation_deg:.2f} deg")
    print(f"  {mesh_result.message}")

    # Export parts as STL (binary) in their natural build orientation (axis along Z)
    # Three.js will handle positioning using the same transforms as position_for_mesh()
    from build123d import export_stl

    worm_path = output_dir / "worm.stl"
    wheel_path = output_dir / "wheel.stl"

    print(f"Exporting worm to {worm_path}...")
    export_stl(worm, str(worm_path), tolerance=0.001, angular_tolerance=0.1)

    print(f"Exporting wheel to {wheel_path}...")
    export_stl(wheel, str(wheel_path), tolerance=0.001, angular_tolerance=0.1)

    # Write metadata for Three.js positioning
    # In build123d (Z-up), position_for_mesh() does:
    #   - Wheel: at origin, axis Z, rotate by optimal_rotation_deg around Z
    #   - Worm: rotate -90° around Y (axis Z→X), translate to (0, centre_distance, 0)
    # STL preserves the Z-up coordinate system (no conversion like glTF).
    # Three.js is Y-up, so the viewer must rotate the whole scene or handle axes.
    design_info = {
        "centre_distance_mm": design.assembly.centre_distance_mm,
        "ratio": design.assembly.ratio,
        "num_starts": design.worm.num_starts,
        "num_teeth": design.wheel.num_teeth,
        "optimal_rotation_deg": mesh_result.optimal_rotation_deg,
        "hand": design.assembly.hand.value,
    }
    info_path = output_dir / "design-info.json"
    with open(info_path, "w") as f:
        json.dump(design_info, f, indent=2)

    print(f"\nDone! Files written to {output_dir}/")
    print(f"  worm.stl:         {worm_path.stat().st_size / 1024:.1f} KB")
    print(f"  wheel.stl:        {wheel_path.stat().st_size / 1024:.1f} KB")
    print(f"  design-info.json: {json.dumps(design_info)}")


if __name__ == "__main__":
    main()
