"""
Command-line interface for worm gear geometry generation.
"""

import argparse
import sys
from pathlib import Path

from .io import load_design_json
from .worm import WormGeometry
from .wheel import WheelGeometry
from .features import BoreFeature, KeywayFeature, calculate_default_bore, get_din_6885_keyway


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate CNC-ready STEP files for worm gear pairs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with auto-calculated bores and DIN 6885 keyways (default)
  wormgear-geometry design.json

  # Generate solid parts without bores
  wormgear-geometry design.json --no-bore

  # Override bore sizes (keyways auto-sized to match)
  wormgear-geometry design.json --worm-bore 8 --wheel-bore 12

  # Bores but no keyways
  wormgear-geometry design.json --no-keyway

  # View in OCP viewer without saving
  wormgear-geometry design.json --view --no-save

  # Custom worm length and smoother geometry
  wormgear-geometry design.json --worm-length 50 --sections 72
        """
    )

    parser.add_argument(
        'design_file',
        type=str,
        help='JSON file from wormgearcalc (Tool 1)'
    )

    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='Output directory for STEP files (default: current directory)'
    )

    parser.add_argument(
        '--worm-length',
        type=float,
        default=40.0,
        help='Worm length in mm (default: 40)'
    )

    parser.add_argument(
        '--wheel-width',
        type=float,
        default=None,
        help='Wheel face width in mm (default: auto-calculated)'
    )

    parser.add_argument(
        '--sections',
        type=int,
        default=36,
        help='Worm sections per turn for smoothness (default: 36)'
    )

    parser.add_argument(
        '--worm-only',
        action='store_true',
        help='Generate only the worm'
    )

    parser.add_argument(
        '--wheel-only',
        action='store_true',
        help='Generate only the wheel'
    )

    parser.add_argument(
        '--view',
        action='store_true',
        help='View in OCP viewer (requires ocp_vscode extension)'
    )

    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save STEP files (use with --view)'
    )

    parser.add_argument(
        '--mesh-aligned',
        action='store_true',
        help='Rotate wheel by half tooth pitch for mesh alignment in viewer'
    )

    parser.add_argument(
        '--hobbed',
        action='store_true',
        help='Generate hobbed wheel with throated teeth (default: helical without throating)'
    )

    # Bore and keyway options (defaults: auto-calculated bore with keyway)
    parser.add_argument(
        '--no-bore',
        action='store_true',
        help='Generate solid parts without bores (default: auto-calculated bores)'
    )

    parser.add_argument(
        '--no-keyway',
        action='store_true',
        help='Omit keyways (default: DIN 6885 keyways added with bores)'
    )

    parser.add_argument(
        '--worm-bore',
        type=float,
        default=None,
        help='Override worm bore diameter in mm (default: auto ~25%% of pitch diameter)'
    )

    parser.add_argument(
        '--wheel-bore',
        type=float,
        default=None,
        help='Override wheel bore diameter in mm (default: auto ~25%% of pitch diameter)'
    )

    args = parser.parse_args()

    # Load design
    try:
        print(f"Loading design from {args.design_file}...")
        design = load_design_json(args.design_file)
    except Exception as e:
        print(f"Error loading design: {e}", file=sys.stderr)
        return 1

    # Determine what to generate
    generate_worm = not args.wheel_only
    generate_wheel = not args.worm_only

    worm = None
    wheel = None

    # Generate worm
    if generate_worm:
        # Determine bore diameter (auto-calculate or override)
        worm_bore = None
        worm_keyway = None
        worm_bore_diameter = None

        if not args.no_bore:
            if args.worm_bore is not None:
                worm_bore_diameter = args.worm_bore
            else:
                # Auto-calculate bore
                worm_bore_diameter = calculate_default_bore(
                    design.worm.pitch_diameter_mm,
                    design.worm.root_diameter_mm
                )

            worm_bore = BoreFeature(diameter=worm_bore_diameter)

            # Add keyway unless disabled
            if not args.no_keyway:
                worm_keyway = KeywayFeature()

        # Build description
        features_desc = ""
        if worm_bore:
            features_desc += f", bore {worm_bore_diameter}mm"
            if worm_keyway:
                features_desc += " + keyway"

        print(f"\nGenerating worm ({design.worm.num_starts}-start, module {design.worm.module_mm}mm{features_desc})...")
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=args.worm_length,
            sections_per_turn=args.sections,
            bore=worm_bore,
            keyway=worm_keyway
        )
        worm = worm_geo.build()
        print(f"  Volume: {worm.volume:.2f} mm³")

    # Generate wheel
    if generate_wheel:
        # Determine bore diameter (auto-calculate or override)
        wheel_bore = None
        wheel_keyway = None
        wheel_bore_diameter = None

        if not args.no_bore:
            if args.wheel_bore is not None:
                wheel_bore_diameter = args.wheel_bore
            else:
                # Auto-calculate bore
                wheel_bore_diameter = calculate_default_bore(
                    design.wheel.pitch_diameter_mm,
                    design.wheel.root_diameter_mm
                )

            wheel_bore = BoreFeature(diameter=wheel_bore_diameter)

            # Add keyway unless disabled
            if not args.no_keyway:
                wheel_keyway = KeywayFeature()

        # Build description
        wheel_type_desc = "hobbed (throated)" if args.hobbed else "helical"
        features_desc = ""
        if wheel_bore:
            features_desc += f", bore {wheel_bore_diameter}mm"
            if wheel_keyway:
                features_desc += " + keyway"

        print(f"\nGenerating wheel ({design.wheel.num_teeth} teeth, module {design.wheel.module_mm}mm, {wheel_type_desc}{features_desc})...")
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=args.wheel_width,
            throated=args.hobbed,
            bore=wheel_bore,
            keyway=wheel_keyway
        )
        wheel = wheel_geo.build()
        print(f"  Volume: {wheel.volume:.2f} mm³")

    # Save STEP files
    if not args.no_save:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        from build123d import export_step

        if worm is not None:
            output_file = output_dir / f"worm_m{design.worm.module_mm}_z{design.worm.num_starts}.step"
            export_step(worm, str(output_file))
            print(f"  Saved: {output_file}")

        if wheel is not None:
            output_file = output_dir / f"wheel_m{design.wheel.module_mm}_z{design.wheel.num_teeth}.step"
            export_step(wheel, str(output_file))
            print(f"  Saved: {output_file}")

    # View in OCP viewer
    if args.view:
        try:
            from ocp_vscode import show
            from build123d import Rot, Pos

            # Position worm to mesh with wheel
            if wheel is not None and worm is not None:
                # Move worm to centre distance, rotate 90° so its axis is horizontal (along Y)
                centre_distance = design.assembly.centre_distance_mm
                worm_positioned = Pos(centre_distance, 0, 0) * Rot(X=90) * worm

                # Optionally rotate wheel by half a tooth pitch for mesh alignment
                if args.mesh_aligned:
                    z = design.wheel.num_teeth
                    tooth_pitch_angle = 360 / z
                    wheel_rotation = tooth_pitch_angle / 2
                    wheel_positioned = Rot(Z=wheel_rotation) * wheel
                else:
                    wheel_positioned = wheel

                show(wheel_positioned, worm_positioned, names=["wheel", "worm"], colors=["steelblue", "orange"])
            elif wheel is not None:
                show(wheel, names=["wheel"], colors=["steelblue"])
            elif worm is not None:
                show(worm, names=["worm"], colors=["orange"])
            print("\nDisplayed in OCP viewer")

        except ImportError:
            print("\nWarning: ocp_vscode not available for viewing", file=sys.stderr)
            print("Install with: pip install ocp_vscode", file=sys.stderr)

    # Summary
    print(f"\nDesign summary:")
    print(f"  Ratio: {design.assembly.ratio}:1")
    print(f"  Centre distance: {design.assembly.centre_distance_mm:.2f} mm")
    print(f"  Pressure angle: {design.assembly.pressure_angle_deg}°")

    # Bore/keyway summary with override hints
    if not args.no_bore:
        print(f"\nBore & keyway (auto-calculated):")
        if generate_worm and worm_bore_diameter:
            keyway_dims = get_din_6885_keyway(worm_bore_diameter)
            keyway_info = ""
            if keyway_dims and not args.no_keyway:
                keyway_info = f", keyway {keyway_dims[0]}x{keyway_dims[2]}mm (DIN 6885)"
            override_note = "" if args.worm_bore else " (override: --worm-bore X)"
            print(f"  Worm:  {worm_bore_diameter}mm{keyway_info}{override_note}")

        if generate_wheel and wheel_bore_diameter:
            keyway_dims = get_din_6885_keyway(wheel_bore_diameter)
            keyway_info = ""
            if keyway_dims and not args.no_keyway:
                keyway_info = f", keyway {keyway_dims[0]}x{keyway_dims[3]}mm (DIN 6885)"
            override_note = "" if args.wheel_bore else " (override: --wheel-bore X)"
            print(f"  Wheel: {wheel_bore_diameter}mm{keyway_info}{override_note}")

        if not args.no_keyway:
            print(f"\n  To omit keyways: --no-keyway")
        print(f"  To generate solid parts: --no-bore")

    return 0


if __name__ == '__main__':
    sys.exit(main())
