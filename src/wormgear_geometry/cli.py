"""
Command-line interface for worm gear geometry generation.
"""

import argparse
import sys
from pathlib import Path

from .io import (
    load_design_json,
    save_design_json,
    WormGearDesign,
    ManufacturingParams,
    ManufacturingFeatures
)
from .worm import WormGeometry
from .globoid_worm import GloboidWormGeometry
from .wheel import WheelGeometry
from .virtual_hobbing import VirtualHobbingWheelGeometry
from .features import (
    BoreFeature,
    KeywayFeature,
    SetScrewFeature,
    HubFeature,
    calculate_default_bore,
    get_din_6885_keyway,
    get_set_screw_size
)


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

  # Add set screw holes for shaft retention (auto-sized from bore)
  wormgear-geometry design.json --set-screw

  # Set screws with specific size and count
  wormgear-geometry design.json --set-screw --set-screw-size M4 --set-screw-count 2

  # Extended hub for bearing support
  wormgear-geometry design.json --hub-type extended --hub-length 15

  # Flanged hub with bolt holes for mounting
  wormgear-geometry design.json --hub-type flanged --flange-diameter 60 --flange-bolts 4

  # Bores but no keyways
  wormgear-geometry design.json --no-keyway

  # View in OCP viewer without saving
  wormgear-geometry design.json --view --no-save

  # Custom worm length and smoother geometry
  wormgear-geometry design.json --worm-length 50 --sections 72

  # Save extended JSON with all manufacturing features for reproducibility
  wormgear-geometry design.json --set-screw --hub-type extended --save-json complete_design.json

  # Generate globoid (hourglass) worm for 30-50% higher load capacity
  wormgear-geometry design.json --globoid

  # For 3D printing: use ZK profile (slightly convex flanks)
  wormgear-geometry design.json --profile ZK

  # For CNC machining: use ZA profile (straight flanks, default)
  wormgear-geometry design.json --profile ZA
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
        '--save-json',
        type=str,
        default=None,
        help='Save extended JSON with all manufacturing features (makes design fully reproducible)'
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

    parser.add_argument(
        '--globoid',
        action='store_true',
        help='Generate globoid (double-enveloping) worm with hourglass shape for 30-50%% higher load capacity'
    )

    parser.add_argument(
        '--profile',
        type=str,
        choices=['ZA', 'ZK', 'za', 'zk'],
        default='ZA',
        help='Tooth profile type per DIN 3975: ZA=straight flanks for CNC (default), ZK=convex for 3D printing'
    )

    # Experimental virtual hobbing
    parser.add_argument(
        '--virtual-hobbing',
        action='store_true',
        help='EXPERIMENTAL: Use virtual hobbing simulation for wheel (more accurate but slower)'
    )

    parser.add_argument(
        '--hobbing-steps',
        type=int,
        default=72,
        help='Number of steps for virtual hobbing (default: 72, higher=more accurate but slower)'
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

    # Set screw options (default: no set screws unless explicitly requested)
    parser.add_argument(
        '--set-screw',
        action='store_true',
        help='Add set screw holes for shaft retention (requires bore)'
    )

    parser.add_argument(
        '--set-screw-size',
        type=str,
        default=None,
        help='Override set screw size (e.g., "M3", "M4") - auto-sized from bore if not specified'
    )

    parser.add_argument(
        '--set-screw-count',
        type=int,
        default=1,
        help='Number of set screws (1-3, default: 1, evenly distributed)'
    )

    # Hub options (for wheel only, default: flush hub)
    parser.add_argument(
        '--hub-type',
        type=str,
        choices=['flush', 'extended', 'flanged'],
        default='flush',
        help='Hub type for wheel mounting (default: flush)'
    )

    parser.add_argument(
        '--hub-length',
        type=float,
        default=10.0,
        help='Hub extension length in mm for extended/flanged hubs (default: 10mm)'
    )

    parser.add_argument(
        '--flange-diameter',
        type=float,
        default=None,
        help='Flange outer diameter in mm (for flanged hub, default: auto-sized)'
    )

    parser.add_argument(
        '--flange-thickness',
        type=float,
        default=5.0,
        help='Flange thickness in mm (for flanged hub, default: 5mm)'
    )

    parser.add_argument(
        '--flange-bolts',
        type=int,
        default=4,
        help='Number of bolt holes in flange (for flanged hub, 0-8, default: 4)'
    )

    parser.add_argument(
        '--bolt-diameter',
        type=float,
        default=None,
        help='Bolt hole diameter in mm (for flanged hub, default: auto-sized)'
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
        worm_set_screw = None
        worm_bore_diameter = None

        worm_thin_rim_warning = False
        if not args.no_bore:
            if args.worm_bore is not None:
                worm_bore_diameter = args.worm_bore
                # Check if user-specified bore has thin rim
                actual_rim = (design.worm.root_diameter_mm - worm_bore_diameter) / 2
                worm_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
            else:
                # Auto-calculate bore (may return None for very small gears)
                worm_bore_diameter, worm_thin_rim_warning = calculate_default_bore(
                    design.worm.pitch_diameter_mm,
                    design.worm.root_diameter_mm
                )

            if worm_bore_diameter is not None:
                worm_bore = BoreFeature(diameter=worm_bore_diameter)

                # Add keyway unless disabled or bore too small for DIN 6885
                if not args.no_keyway and worm_bore_diameter >= 6.0:
                    worm_keyway = KeywayFeature()

                # Add set screw if requested
                if args.set_screw:
                    # Parse size if specified (e.g., "M4" -> ("M4", 4.0))
                    if args.set_screw_size:
                        # Extract diameter from size string (e.g., "M4" -> 4.0)
                        try:
                            size_str = args.set_screw_size.upper()
                            if size_str.startswith('M'):
                                diameter = float(size_str[1:])
                                worm_set_screw = SetScrewFeature(
                                    size=size_str,
                                    diameter=diameter,
                                    count=args.set_screw_count
                                )
                            else:
                                print(f"  WARNING: Invalid set screw size '{args.set_screw_size}', using auto-size")
                                worm_set_screw = SetScrewFeature(count=args.set_screw_count)
                        except ValueError:
                            print(f"  WARNING: Could not parse set screw size '{args.set_screw_size}', using auto-size")
                            worm_set_screw = SetScrewFeature(count=args.set_screw_count)
                    else:
                        worm_set_screw = SetScrewFeature(count=args.set_screw_count)

        # Build description
        features_desc = ""
        if worm_bore:
            features_desc += f", bore {worm_bore_diameter}mm"
            if worm_keyway:
                features_desc += " + keyway"
            elif worm_bore_diameter < 6.0:
                features_desc += " (no keyway - below DIN 6885 range)"
            if worm_set_screw:
                screw_size, _ = worm_set_screw.get_screw_specs(worm_bore_diameter)
                screw_desc = f"{screw_size}"
                if worm_set_screw.count > 1:
                    screw_desc += f" x{worm_set_screw.count}"
                features_desc += f" + set screw ({screw_desc})"

        worm_type_desc = "globoid (hourglass)" if args.globoid else "cylindrical"
        profile_desc = "ZK/3D-print" if args.profile.upper() == "ZK" else "ZA/CNC"
        print(f"\nGenerating worm ({worm_type_desc}, {design.worm.num_starts}-start, module {design.worm.module_mm}mm, {profile_desc}{features_desc})...")

        profile = args.profile.upper()
        if args.globoid:
            worm_geo = GloboidWormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
                length=args.worm_length,
                sections_per_turn=args.sections,
                bore=worm_bore,
                keyway=worm_keyway,
                set_screw=worm_set_screw,
                profile=profile
            )
        else:
            worm_geo = WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=args.worm_length,
                sections_per_turn=args.sections,
                bore=worm_bore,
                keyway=worm_keyway,
                set_screw=worm_set_screw,
                profile=profile
            )

        worm = worm_geo.build()
        print(f"  Volume: {worm.volume:.2f} mm³")

    # Generate wheel
    if generate_wheel:
        # Determine bore diameter (auto-calculate or override)
        wheel_bore = None
        wheel_keyway = None
        wheel_set_screw = None
        wheel_bore_diameter = None

        wheel_thin_rim_warning = False
        if not args.no_bore:
            if args.wheel_bore is not None:
                wheel_bore_diameter = args.wheel_bore
                # Check if user-specified bore has thin rim
                actual_rim = (design.wheel.root_diameter_mm - wheel_bore_diameter) / 2
                wheel_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
            else:
                # Auto-calculate bore (may return None for very small gears)
                wheel_bore_diameter, wheel_thin_rim_warning = calculate_default_bore(
                    design.wheel.pitch_diameter_mm,
                    design.wheel.root_diameter_mm
                )

            if wheel_bore_diameter is not None:
                wheel_bore = BoreFeature(diameter=wheel_bore_diameter)

                # Add keyway unless disabled or bore too small for DIN 6885
                if not args.no_keyway and wheel_bore_diameter >= 6.0:
                    wheel_keyway = KeywayFeature()

                # Add set screw if requested
                if args.set_screw:
                    # Parse size if specified (e.g., "M4" -> ("M4", 4.0))
                    if args.set_screw_size:
                        # Extract diameter from size string (e.g., "M4" -> 4.0)
                        try:
                            size_str = args.set_screw_size.upper()
                            if size_str.startswith('M'):
                                diameter = float(size_str[1:])
                                wheel_set_screw = SetScrewFeature(
                                    size=size_str,
                                    diameter=diameter,
                                    count=args.set_screw_count
                                )
                            else:
                                print(f"  WARNING: Invalid set screw size '{args.set_screw_size}', using auto-size")
                                wheel_set_screw = SetScrewFeature(count=args.set_screw_count)
                        except ValueError:
                            print(f"  WARNING: Could not parse set screw size '{args.set_screw_size}', using auto-size")
                            wheel_set_screw = SetScrewFeature(count=args.set_screw_count)
                    else:
                        wheel_set_screw = SetScrewFeature(count=args.set_screw_count)

        # Create hub feature
        wheel_hub = None
        if args.hub_type != "flush":
            wheel_hub = HubFeature(
                hub_type=args.hub_type,
                length=args.hub_length,
                flange_diameter=args.flange_diameter,
                flange_thickness=args.flange_thickness,
                bolt_holes=args.flange_bolts,
                bolt_diameter=args.bolt_diameter
            )

        # Build description
        wheel_type_desc = "hobbed (throated)" if args.hobbed else "helical"
        features_desc = ""
        if wheel_bore:
            features_desc += f", bore {wheel_bore_diameter}mm"
            if wheel_keyway:
                features_desc += " + keyway"
            elif wheel_bore_diameter < 6.0:
                features_desc += " (no keyway - below DIN 6885 range)"
            if wheel_set_screw:
                screw_size, _ = wheel_set_screw.get_screw_specs(wheel_bore_diameter)
                screw_desc = f"{screw_size}"
                if wheel_set_screw.count > 1:
                    screw_desc += f" x{wheel_set_screw.count}"
                features_desc += f" + set screw ({screw_desc})"

        if wheel_hub and wheel_hub.hub_type != "flush":
            hub_desc = f"{wheel_hub.hub_type} hub ({wheel_hub.length}mm"
            if wheel_hub.hub_type == "flanged":
                flange_dia = wheel_hub.flange_diameter if wheel_hub.flange_diameter else "auto"
                hub_desc += f", flange {flange_dia}mm"
                if wheel_hub.bolt_holes > 0:
                    hub_desc += f", {wheel_hub.bolt_holes} bolts"
            hub_desc += ")"
            features_desc += f", {hub_desc}"

        profile = args.profile.upper()
        profile_desc = "ZK/3D-print" if profile == "ZK" else "ZA/CNC"

        if args.virtual_hobbing:
            # EXPERIMENTAL: Virtual hobbing simulation
            # Pass the actual worm geometry as hob if available (important for globoid)
            hob_geo = worm if worm is not None else None
            hob_type = "globoid" if args.globoid and hob_geo else "cylindrical"
            print(f"\nGenerating wheel ({design.wheel.num_teeth} teeth, module {design.wheel.module_mm}mm, VIRTUAL HOBBING [EXPERIMENTAL], {profile_desc}{features_desc})...")
            print(f"  Using {args.hobbing_steps} hobbing steps, {hob_type} hob")
            wheel_geo = VirtualHobbingWheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=args.wheel_width,
                hobbing_steps=args.hobbing_steps,
                bore=wheel_bore,
                keyway=wheel_keyway,
                set_screw=wheel_set_screw,
                hub=wheel_hub,
                profile=profile,
                hob_geometry=hob_geo
            )
        else:
            print(f"\nGenerating wheel ({design.wheel.num_teeth} teeth, module {design.wheel.module_mm}mm, {wheel_type_desc}, {profile_desc}{features_desc})...")
            wheel_geo = WheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=args.wheel_width,
                throated=args.hobbed,
                bore=wheel_bore,
                keyway=wheel_keyway,
                set_screw=wheel_set_screw,
                hub=wheel_hub,
                profile=profile
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
    profile_name = "ZK (convex, 3D printing)" if args.profile.upper() == "ZK" else "ZA (straight, CNC)"
    print(f"\nDesign summary:")
    print(f"  Ratio: {design.assembly.ratio}:1")
    print(f"  Centre distance: {design.assembly.centre_distance_mm:.2f} mm")
    print(f"  Pressure angle: {design.assembly.pressure_angle_deg}°")
    print(f"  Tooth profile: {profile_name} (DIN 3975)")

    # Bore/keyway summary with override hints
    if not args.no_bore:
        has_any_bore = (generate_worm and worm_bore_diameter) or (generate_wheel and wheel_bore_diameter)
        if has_any_bore:
            print(f"\nBore & keyway:")
            if generate_worm:
                if worm_bore_diameter:
                    keyway_dims = get_din_6885_keyway(worm_bore_diameter)
                    keyway_info = ""
                    if keyway_dims and not args.no_keyway:
                        keyway_info = f", keyway {keyway_dims[0]}x{keyway_dims[2]}mm (DIN 6885)"
                    elif worm_bore_diameter < 6.0:
                        keyway_info = " (no keyway - below DIN 6885 range)"
                    override_note = "" if args.worm_bore else " (override: --worm-bore X)"
                    worm_rim = (design.worm.root_diameter_mm - worm_bore_diameter) / 2
                    print(f"  Worm:  {worm_bore_diameter}mm{keyway_info}, rim {worm_rim:.2f}mm{override_note}")
                else:
                    print(f"  Worm:  solid (too small for bore)")

            if generate_wheel:
                if wheel_bore_diameter:
                    keyway_dims = get_din_6885_keyway(wheel_bore_diameter)
                    keyway_info = ""
                    if keyway_dims and not args.no_keyway:
                        keyway_info = f", keyway {keyway_dims[0]}x{keyway_dims[3]}mm (DIN 6885)"
                    elif wheel_bore_diameter < 6.0:
                        keyway_info = " (no keyway - below DIN 6885 range)"
                    override_note = "" if args.wheel_bore else " (override: --wheel-bore X)"
                    wheel_rim = (design.wheel.root_diameter_mm - wheel_bore_diameter) / 2
                    print(f"  Wheel: {wheel_bore_diameter}mm{keyway_info}, rim {wheel_rim:.2f}mm{override_note}")
                else:
                    print(f"  Wheel: solid (too small for bore)")

            # Print warnings for thin rims
            if (generate_worm and worm_thin_rim_warning) or (generate_wheel and wheel_thin_rim_warning):
                print(f"\n  Warning: thin rim on small bore - handle with care")

            print(f"\n  To generate solid parts: --no-bore")

    # Save extended JSON with manufacturing features
    if args.save_json:
        # Collect worm manufacturing features
        worm_features = None
        if worm_bore_diameter or worm_set_screw:
            keyway_dims = get_din_6885_keyway(worm_bore_diameter) if worm_bore_diameter else None
            worm_features = ManufacturingFeatures(
                bore_diameter=worm_bore_diameter,
                keyway_width=keyway_dims[0] if keyway_dims and worm_keyway else None,
                keyway_depth=keyway_dims[2] if keyway_dims and worm_keyway else None,
                set_screw_size=worm_set_screw.size if worm_set_screw else None,
                set_screw_count=worm_set_screw.count if worm_set_screw else None
            )

        # Collect wheel manufacturing features
        wheel_features = None
        if wheel_bore_diameter or wheel_set_screw or wheel_hub:
            keyway_dims = get_din_6885_keyway(wheel_bore_diameter) if wheel_bore_diameter else None
            wheel_features = ManufacturingFeatures(
                bore_diameter=wheel_bore_diameter,
                keyway_width=keyway_dims[0] if keyway_dims and wheel_keyway else None,
                keyway_depth=keyway_dims[3] if keyway_dims and wheel_keyway else None,
                set_screw_size=wheel_set_screw.size if wheel_set_screw else None,
                set_screw_count=wheel_set_screw.count if wheel_set_screw else None,
                hub_type=wheel_hub.hub_type if wheel_hub else None,
                hub_length=wheel_hub.length if wheel_hub else None,
                flange_diameter=wheel_hub.flange_diameter if wheel_hub else None,
                flange_thickness=wheel_hub.flange_thickness if wheel_hub else None,
                flange_bolts=wheel_hub.bolt_holes if wheel_hub else None,
                bolt_diameter=wheel_hub.bolt_diameter if wheel_hub else None
            )

        # Create manufacturing parameters
        manufacturing = ManufacturingParams(
            worm_type="globoid" if args.globoid else "cylindrical",
            worm_length=args.worm_length,
            wheel_width=args.wheel_width,
            wheel_throated=args.hobbed,
            profile=args.profile.upper(),
            worm_features=worm_features,
            wheel_features=wheel_features
        )

        # Create complete design with manufacturing parameters
        complete_design = WormGearDesign(
            worm=design.worm,
            wheel=design.wheel,
            assembly=design.assembly,
            manufacturing=manufacturing
        )

        # Save to file
        output_path = Path(args.save_json)
        save_design_json(complete_design, output_path)
        print(f"\nSaved extended JSON: {output_path}")
        print(f"  This JSON includes all manufacturing features and can fully reproduce this design")

    return 0


if __name__ == '__main__':
    sys.exit(main())
