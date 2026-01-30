"""
Command-line interface for worm gear geometry generation.
"""

import argparse
import sys
from pathlib import Path

from ..io.loaders import (
    load_design_json,
    save_design_json,
    WormGearDesign,
    ManufacturingParams,
    ManufacturingFeatures
)
from ..enums import WormType, WormProfile, BoreType
from ..core.worm import WormGeometry
from ..core.globoid_worm import GloboidWormGeometry
from ..core.wheel import WheelGeometry
from ..core.virtual_hobbing import VirtualHobbingWheelGeometry
from ..core.features import (
    BoreFeature,
    KeywayFeature,
    DDCutFeature,
    SetScrewFeature,
    HubFeature,
    calculate_default_bore,
    calculate_default_ddcut,
    get_din_6885_keyway,
    get_set_screw_size
)
from ..core.mesh_alignment import (
    find_optimal_mesh_rotation,
    position_for_mesh,
    mesh_alignment_to_dict,
)
from ..core.rim_thickness import (
    measure_rim_thickness,
    rim_thickness_to_dict,
    WHEEL_RIM_WARNING_THRESHOLD_MM,
    WORM_RIM_WARNING_THRESHOLD_MM,
)
from ..io.loaders import MeshAlignment, WormPosition, MeasuredGeometry, MeasurementPoint


def interference_check(
    worm,
    wheel,
    centre_distance: float,
    worm_lead: float,
    wheel_teeth: int,
    steps: int = 36
) -> bool:
    """
    Check for interference between worm and wheel at multiple rotation angles.

    Positions the worm at centre_distance from the wheel (along X axis),
    with worm axis along Y (perpendicular to wheel axis along Z).

    Rotates both parts through one complete mesh cycle and checks for
    boolean intersection at each step.

    Args:
        worm: Worm Part geometry
        wheel: Wheel Part geometry
        centre_distance: Distance between axes in mm
        worm_lead: Worm lead (axial advance per revolution) in mm
        wheel_teeth: Number of wheel teeth
        steps: Number of rotation steps to check

    Returns:
        True if no interference found, False if interference detected
    """
    from build123d import Pos, Rot, Part
    import math

    # For one complete wheel tooth engagement, the worm rotates by:
    # wheel_rotation = 360 / wheel_teeth (one tooth pitch)
    # worm_rotation = wheel_rotation * wheel_teeth / worm_starts = 360 degrees
    # But since worm has lead, we need to track the kinematic relationship

    # The gear ratio: wheel rotates 1/ratio per worm revolution
    # For checking, we'll rotate the worm through 360 degrees
    # and the wheel through 360/ratio degrees

    # Position worm: translate to centre distance, rotate 90° so axis is along Y
    worm_base = Pos(centre_distance, 0, 0) * Rot(X=90) * worm

    interference_found = False
    max_interference_volume = 0.0
    worst_angle = 0.0

    print(f"  Worm at X={centre_distance}mm, axis along Y")
    print(f"  Wheel at origin, axis along Z")
    print(f"  Checking {steps} positions through 360° worm rotation...")

    for i in range(steps):
        # Worm rotation angle (0 to 360 degrees)
        worm_angle = (360.0 / steps) * i

        # Corresponding wheel rotation (kinematically linked)
        # When worm rotates 360°, wheel rotates (360/ratio)°
        # ratio = wheel_teeth / worm_starts, but for single-start: ratio = wheel_teeth
        wheel_angle = worm_angle / wheel_teeth

        # Apply rotations
        # Worm rotates around its axis (Y after positioning)
        worm_rotated = Pos(centre_distance, 0, 0) * Rot(X=90) * Rot(Z=worm_angle) * worm

        # Wheel rotates around Z
        wheel_rotated = Rot(Z=wheel_angle) * wheel

        # Check intersection
        try:
            intersection = worm_rotated & wheel_rotated
            if hasattr(intersection, 'volume') and intersection.volume > 0.001:
                interference_found = True
                if intersection.volume > max_interference_volume:
                    max_interference_volume = intersection.volume
                    worst_angle = worm_angle
                print(f"  ⚠️  Step {i+1}/{steps}: Interference at worm={worm_angle:.1f}°, wheel={wheel_angle:.1f}° - volume={intersection.volume:.4f}mm³")
        except Exception as e:
            # Boolean operation failed - might indicate touching surfaces
            print(f"  ⚠️  Step {i+1}/{steps}: Boolean check failed at worm={worm_angle:.1f}° ({e})")

    # Summary
    if interference_found:
        print(f"\n  ❌ INTERFERENCE DETECTED")
        print(f"     Maximum interference volume: {max_interference_volume:.4f} mm³")
        print(f"     Worst at worm angle: {worst_angle:.1f}°")
        print(f"\n  Suggestions:")
        print(f"     - Increase backlash in calculator")
        print(f"     - Use virtual hobbing (--virtual-hobbing) for accurate wheel teeth")
        print(f"     - Check that profile type matches between worm and wheel")
        return False
    else:
        print(f"\n  ✓ No interference detected at any rotation angle")
        print(f"    Gear pair should mesh correctly")
        return True


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

  # Tooth profiles per DIN 3975:
  wormgear-geometry design.json --profile ZA  # Straight flanks (default, CNC)
  wormgear-geometry design.json --profile ZK  # Circular arc (3D printing)
  wormgear-geometry design.json --profile ZI  # Involute (hobbing)

  # Check for interference between worm and wheel
  wormgear-geometry design.json --check-interference
  wormgear-geometry design.json --check-interference --interference-steps 72  # More thorough
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
        '--check-interference',
        action='store_true',
        help='Check for interference between worm and wheel at multiple rotation angles'
    )

    parser.add_argument(
        '--interference-steps',
        type=int,
        default=36,
        help='Number of rotation steps for interference check (default: 36 = every 10 degrees)'
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
        choices=['ZA', 'ZK', 'ZI', 'za', 'zk', 'zi'],
        default=None,
        help='Tooth profile type per DIN 3975: ZA=straight flanks/CNC (default), ZK=circular arc/3D print, ZI=involute/hobbing'
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

    # DD-cut options (alternative to keyways for small diameter bores)
    parser.add_argument(
        '--dd-cut',
        action='store_true',
        help='Use double-D cuts instead of keyways (for small diameter bores < 6mm)'
    )

    parser.add_argument(
        '--worm-ddcut-depth',
        type=float,
        default=None,
        help='Worm DD-cut flat depth in mm (default: auto ~15%% of bore diameter)'
    )

    parser.add_argument(
        '--wheel-ddcut-depth',
        type=float,
        default=None,
        help='Wheel DD-cut flat depth in mm (default: auto ~15%% of bore diameter)'
    )

    parser.add_argument(
        '--ddcut-depth-percent',
        type=float,
        default=15.0,
        help='DD-cut depth as percentage of bore diameter (default: 15.0 for ~70%% flat-to-flat). Common: 10%% (80%% f-t-f), 15%% (70%% f-t-f), 20%% (60%% f-t-f)'
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
    worm_rim_result = None
    wheel_rim_result = None

    # Get features from JSON if present (source of truth)
    json_worm_features = design.features.worm if design.features else None
    json_wheel_features = design.features.wheel if design.features else None

    # Get manufacturing params from JSON (CLI args override)
    json_mfg = design.manufacturing
    use_globoid = args.globoid or (design.worm.type == WormType.GLOBOID if design.worm.type else False)
    # CLI profile takes precedence if explicitly provided, otherwise use JSON or default to ZA
    if args.profile is not None:
        use_profile = args.profile.upper()
    elif json_mfg and json_mfg.profile:
        use_profile = json_mfg.profile
    else:
        use_profile = 'ZA'
    use_virtual_hobbing = args.virtual_hobbing or (json_mfg.virtual_hobbing if json_mfg else False)
    use_hobbing_steps = args.hobbing_steps if args.hobbing_steps != 72 else (json_mfg.hobbing_steps if json_mfg else 72)
    use_sections = args.sections if args.sections != 36 else (json_mfg.sections_per_turn if json_mfg else 36)
    use_worm_length = args.worm_length if args.worm_length != 40.0 else (json_mfg.worm_length_mm if json_mfg and json_mfg.worm_length_mm else 40.0)
    use_wheel_width = args.wheel_width if args.wheel_width is not None else (json_mfg.wheel_width_mm if json_mfg and json_mfg.wheel_width_mm else None)

    # Generate worm
    if generate_worm:
        # Determine bore diameter: CLI arg > JSON features > auto-calculate
        worm_bore = None
        worm_keyway = None
        worm_ddcut = None
        worm_set_screw = None
        worm_bore_diameter = None

        worm_thin_rim_warning = False
        if not args.no_bore:
            if args.worm_bore is not None:
                # CLI override takes priority
                worm_bore_diameter = args.worm_bore
                actual_rim = (design.worm.root_diameter_mm - worm_bore_diameter) / 2
                worm_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
            elif json_worm_features:
                # Check bore_type from JSON features
                json_bore_type = json_worm_features.bore_type
                if json_bore_type == BoreType.NONE:
                    # Explicit none - solid part
                    worm_bore_diameter = None
                elif json_bore_type == BoreType.CUSTOM and json_worm_features.bore_diameter_mm is not None:
                    # Custom bore with explicit diameter
                    worm_bore_diameter = json_worm_features.bore_diameter_mm
                    actual_rim = (design.worm.root_diameter_mm - worm_bore_diameter) / 2
                    worm_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
                else:
                    # Custom bore without diameter - auto-calculate
                    worm_bore_diameter, worm_thin_rim_warning = calculate_default_bore(
                        design.worm.pitch_diameter_mm,
                        design.worm.root_diameter_mm
                    )
            else:
                # No JSON features - auto-calculate bore
                worm_bore_diameter, worm_thin_rim_warning = calculate_default_bore(
                    design.worm.pitch_diameter_mm,
                    design.worm.root_diameter_mm
                )

            if worm_bore_diameter is not None:
                worm_bore = BoreFeature(diameter=worm_bore_diameter)

                # Determine anti-rotation: CLI arg > JSON features > default (keyway if >= 6mm)
                json_anti_rotation = json_worm_features.anti_rotation if json_worm_features else None

                if args.dd_cut or (json_anti_rotation and json_anti_rotation.value == 'ddcut'):
                    # DD-cut requested
                    if args.worm_ddcut_depth:
                        worm_ddcut = DDCutFeature(depth=args.worm_ddcut_depth)
                    else:
                        depth_pct = json_worm_features.ddcut_depth_percent if json_worm_features else args.ddcut_depth_percent
                        worm_ddcut = calculate_default_ddcut(worm_bore_diameter, depth_pct)
                elif args.no_keyway or (json_anti_rotation and json_anti_rotation.value == 'none'):
                    # No keyway explicitly requested
                    pass
                elif worm_bore_diameter >= 6.0:
                    # Default: keyway for bores >= 6mm (unless JSON says none)
                    worm_keyway = KeywayFeature()

                # Add set screw: CLI arg > JSON features
                json_set_screw = json_worm_features.set_screw if json_worm_features else None
                if args.set_screw or json_set_screw:
                    # Parse size: CLI arg > JSON > auto
                    if args.set_screw_size:
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
                    elif json_set_screw:
                        # Use JSON set screw spec
                        size_str = json_set_screw.size.upper()
                        try:
                            diameter = float(size_str[1:]) if size_str.startswith('M') else None
                            worm_set_screw = SetScrewFeature(
                                size=size_str,
                                diameter=diameter,
                                count=json_set_screw.count
                            )
                        except ValueError:
                            worm_set_screw = SetScrewFeature(count=json_set_screw.count)
                    else:
                        worm_set_screw = SetScrewFeature(count=args.set_screw_count)

        # Build description
        features_desc = ""
        if worm_bore:
            features_desc += f", bore {worm_bore_diameter}mm"
            if worm_keyway:
                features_desc += " + keyway"
            elif worm_ddcut:
                ddcut_depth = worm_ddcut.get_depth(worm_bore_diameter)
                features_desc += f" + DD-cut ({ddcut_depth:.1f}mm depth)"
            elif worm_bore_diameter < 6.0:
                features_desc += " (no keyway - below DIN 6885 range)"
            if worm_set_screw:
                screw_size, _ = worm_set_screw.get_screw_specs(worm_bore_diameter)
                screw_desc = f"{screw_size}"
                if worm_set_screw.count > 1:
                    screw_desc += f" x{worm_set_screw.count}"
                features_desc += f" + set screw ({screw_desc})"

        worm_type_desc = "globoid (hourglass)" if use_globoid else "cylindrical"
        profile_upper = use_profile
        if profile_upper == WormProfile.ZK or profile_upper == "ZK":
            profile_desc = "ZK/circular arc"
        elif profile_upper == WormProfile.ZI or profile_upper == "ZI":
            profile_desc = "ZI/involute"
        else:
            profile_desc = "ZA/straight"
        print(f"\nGenerating worm ({worm_type_desc}, {design.worm.num_starts}-start, module {design.worm.module_mm}mm, {profile_desc}{features_desc})...")

        profile = use_profile
        if use_globoid:
            worm_geo = GloboidWormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
                length=use_worm_length,
                sections_per_turn=use_sections,
                bore=worm_bore,
                keyway=worm_keyway,
                ddcut=worm_ddcut,
                set_screw=worm_set_screw,
                profile=profile
            )
        else:
            worm_geo = WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=use_worm_length,
                sections_per_turn=use_sections,
                bore=worm_bore,
                keyway=worm_keyway,
                ddcut=worm_ddcut,
                set_screw=worm_set_screw,
                profile=profile
            )

        worm = worm_geo.build()
        print(f"  Volume: {worm.volume:.2f} mm³")

        # Measure rim thickness if bore is present
        worm_rim_result = None
        if worm_bore_diameter is not None:
            worm_rim_result = measure_rim_thickness(
                part=worm,
                bore_diameter_mm=worm_bore_diameter,
                is_worm=True
            )
            if worm_rim_result is not None:
                print(f"  Rim thickness: {worm_rim_result.minimum_thickness_mm:.2f} mm")
                if worm_rim_result.has_warning:
                    print(f"  WARNING: Rim thickness below {WORM_RIM_WARNING_THRESHOLD_MM}mm threshold")

    # Generate wheel
    if generate_wheel:
        # Determine bore diameter: CLI arg > JSON features > auto-calculate
        wheel_bore = None
        wheel_keyway = None
        wheel_ddcut = None
        wheel_set_screw = None
        wheel_bore_diameter = None

        wheel_thin_rim_warning = False
        if not args.no_bore:
            if args.wheel_bore is not None:
                # CLI override takes priority
                wheel_bore_diameter = args.wheel_bore
                actual_rim = (design.wheel.root_diameter_mm - wheel_bore_diameter) / 2
                wheel_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
            elif json_wheel_features:
                # Check bore_type from JSON features
                json_bore_type = json_wheel_features.bore_type
                if json_bore_type == BoreType.NONE:
                    # Explicit none - solid part
                    wheel_bore_diameter = None
                elif json_bore_type == BoreType.CUSTOM and json_wheel_features.bore_diameter_mm is not None:
                    # Custom bore with explicit diameter
                    wheel_bore_diameter = json_wheel_features.bore_diameter_mm
                    actual_rim = (design.wheel.root_diameter_mm - wheel_bore_diameter) / 2
                    wheel_thin_rim_warning = actual_rim < 1.5 and actual_rim > 0
                else:
                    # Custom bore without diameter - auto-calculate
                    wheel_bore_diameter, wheel_thin_rim_warning = calculate_default_bore(
                        design.wheel.pitch_diameter_mm,
                        design.wheel.root_diameter_mm
                    )
            else:
                # No JSON features - auto-calculate bore
                wheel_bore_diameter, wheel_thin_rim_warning = calculate_default_bore(
                    design.wheel.pitch_diameter_mm,
                    design.wheel.root_diameter_mm
                )

            if wheel_bore_diameter is not None:
                wheel_bore = BoreFeature(diameter=wheel_bore_diameter)

                # Determine anti-rotation: CLI arg > JSON features > default (keyway if >= 6mm)
                json_anti_rotation = json_wheel_features.anti_rotation if json_wheel_features else None

                if args.dd_cut or (json_anti_rotation and json_anti_rotation.value == 'ddcut'):
                    # DD-cut requested
                    if args.wheel_ddcut_depth:
                        wheel_ddcut = DDCutFeature(depth=args.wheel_ddcut_depth)
                    else:
                        depth_pct = json_wheel_features.ddcut_depth_percent if json_wheel_features else args.ddcut_depth_percent
                        wheel_ddcut = calculate_default_ddcut(wheel_bore_diameter, depth_pct)
                elif args.no_keyway or (json_anti_rotation and json_anti_rotation.value == 'none'):
                    # No keyway explicitly requested
                    pass
                elif wheel_bore_diameter >= 6.0:
                    # Default: keyway for bores >= 6mm
                    wheel_keyway = KeywayFeature()

                # Add set screw: CLI arg > JSON features
                json_set_screw = json_wheel_features.set_screw if json_wheel_features else None
                if args.set_screw or json_set_screw:
                    if args.set_screw_size:
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
                    elif json_set_screw:
                        size_str = json_set_screw.size.upper()
                        try:
                            diameter = float(size_str[1:]) if size_str.startswith('M') else None
                            wheel_set_screw = SetScrewFeature(
                                size=size_str,
                                diameter=diameter,
                                count=json_set_screw.count
                            )
                        except ValueError:
                            wheel_set_screw = SetScrewFeature(count=json_set_screw.count)
                    else:
                        wheel_set_screw = SetScrewFeature(count=args.set_screw_count)

        # Create hub feature: CLI arg > JSON features
        wheel_hub = None
        json_hub = json_wheel_features.hub if json_wheel_features else None
        hub_type = args.hub_type if args.hub_type != "flush" else (json_hub.type if json_hub else "flush")
        if hub_type != "flush":
            wheel_hub = HubFeature(
                hub_type=hub_type,
                length=args.hub_length or (json_hub.length_mm if json_hub else None),
                flange_diameter=args.flange_diameter or (json_hub.flange_diameter_mm if json_hub else None),
                flange_thickness=args.flange_thickness or (json_hub.flange_thickness_mm if json_hub else None),
                bolt_holes=args.flange_bolts or (json_hub.bolt_holes if json_hub else None),
                bolt_diameter=args.bolt_diameter or (json_hub.bolt_diameter_mm if json_hub else None)
            )

        # Build description
        wheel_type_desc = "hobbed (throated)" if args.hobbed else "helical"
        features_desc = ""
        if wheel_bore:
            features_desc += f", bore {wheel_bore_diameter}mm"
            if wheel_keyway:
                features_desc += " + keyway"
            elif wheel_ddcut:
                ddcut_depth = wheel_ddcut.get_depth(wheel_bore_diameter)
                features_desc += f" + DD-cut ({ddcut_depth:.1f}mm depth)"
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

        profile = use_profile
        if profile == WormProfile.ZK or profile == "ZK":
            profile_desc = "ZK/circular arc"
        elif profile == WormProfile.ZI or profile == "ZI":
            profile_desc = "ZI/involute"
        else:
            profile_desc = "ZA/straight"

        if use_virtual_hobbing:
            # EXPERIMENTAL: Virtual hobbing simulation
            # Pass the actual worm geometry as hob ONLY for globoid (important for accuracy)
            # For cylindrical, let VirtualHobbingWheelGeometry create a simpler hob internally
            hob_geo = worm if (worm is not None and use_globoid) else None
            hob_type = "globoid" if use_globoid else "cylindrical"
            print(f"\nGenerating wheel ({design.wheel.num_teeth} teeth, module {design.wheel.module_mm}mm, VIRTUAL HOBBING [EXPERIMENTAL], {profile_desc}{features_desc})...")
            print(f"  Using {use_hobbing_steps} hobbing steps, {hob_type} hob")
            wheel_geo = VirtualHobbingWheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=use_wheel_width,
                hobbing_steps=use_hobbing_steps,
                bore=wheel_bore,
                keyway=wheel_keyway,
                ddcut=wheel_ddcut,
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
                face_width=use_wheel_width,
                throated=args.hobbed,
                bore=wheel_bore,
                keyway=wheel_keyway,
                ddcut=wheel_ddcut,
                set_screw=wheel_set_screw,
                hub=wheel_hub,
                profile=profile
            )
        wheel = wheel_geo.build()
        print(f"  Volume: {wheel.volume:.2f} mm³")

        # Measure rim thickness if bore is present
        wheel_rim_result = None
        if wheel_bore_diameter is not None:
            wheel_rim_result = measure_rim_thickness(
                part=wheel,
                bore_diameter_mm=wheel_bore_diameter,
                is_worm=False
            )
            if wheel_rim_result is not None:
                print(f"  Rim thickness: {wheel_rim_result.minimum_thickness_mm:.2f} mm")
                if wheel_rim_result.has_warning:
                    print(f"  WARNING: Rim thickness below {WHEEL_RIM_WARNING_THRESHOLD_MM}mm threshold")

    # Check for interference between worm and wheel
    if args.check_interference and worm is not None and wheel is not None:
        print(f"\nChecking interference ({args.interference_steps} rotation steps)...")
        interference_check(
            worm=worm,
            wheel=wheel,
            centre_distance=design.assembly.centre_distance_mm,
            worm_lead=design.worm.lead_mm,
            wheel_teeth=design.wheel.num_teeth,
            steps=args.interference_steps
        )

    # Calculate mesh alignment (when both parts generated)
    mesh_alignment_result = None
    if worm is not None and wheel is not None:
        print(f"\nCalculating mesh alignment...")
        mesh_alignment_result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=design.assembly.centre_distance_mm,
            num_teeth=design.wheel.num_teeth,
        )
        print(f"  Optimal wheel rotation: {mesh_alignment_result.optimal_rotation_deg:.2f}°")
        print(f"  Interference volume: {mesh_alignment_result.interference_volume_mm3:.4f} mm³")
        print(f"  Status: {mesh_alignment_result.message}")

    # Save STEP files and mesh alignment
    if not args.no_save:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        from build123d import export_step
        import json

        if worm is not None:
            output_file = output_dir / f"worm_m{design.worm.module_mm}_z{design.worm.num_starts}.step"
            export_step(worm, str(output_file))
            print(f"  Saved: {output_file}")

        if wheel is not None:
            output_file = output_dir / f"wheel_m{design.wheel.module_mm}_z{design.wheel.num_teeth}.step"
            export_step(wheel, str(output_file))
            print(f"  Saved: {output_file}")

        # Save combined geometry analysis JSON (mesh alignment + rim measurements)
        if mesh_alignment_result is not None or worm_rim_result is not None or wheel_rim_result is not None:
            from datetime import datetime
            analysis_file = output_dir / f"geometry_analysis_m{design.worm.module_mm}.json"

            analysis_data = {
                "design_info": {
                    "module_mm": design.worm.module_mm,
                    "ratio": design.assembly.ratio,
                    "centre_distance_mm": design.assembly.centre_distance_mm,
                    "worm_starts": design.worm.num_starts,
                    "wheel_teeth": design.wheel.num_teeth,
                },
                "analysis_timestamp": datetime.now().isoformat(),
            }

            # Add mesh alignment data
            if mesh_alignment_result is not None:
                analysis_data["mesh_alignment"] = mesh_alignment_to_dict(mesh_alignment_result)

            # Add rim thickness data
            if worm_rim_result is not None or wheel_rim_result is not None:
                analysis_data["rim_thickness"] = {}
                if worm_rim_result is not None:
                    analysis_data["rim_thickness"]["worm"] = rim_thickness_to_dict(worm_rim_result)
                if wheel_rim_result is not None:
                    analysis_data["rim_thickness"]["wheel"] = rim_thickness_to_dict(wheel_rim_result)

            with open(analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            print(f"  Saved: {analysis_file}")

    # View in OCP viewer
    if args.view:
        try:
            from ocp_vscode import show

            # Position parts for mesh visualization
            if wheel is not None and worm is not None:
                # Use calculated mesh alignment for optimal positioning
                if mesh_alignment_result is not None:
                    wheel_positioned, worm_positioned = position_for_mesh(
                        wheel=wheel,
                        worm=worm,
                        centre_distance_mm=design.assembly.centre_distance_mm,
                        rotation_deg=mesh_alignment_result.optimal_rotation_deg,
                    )
                    print(f"\n  Wheel rotated {mesh_alignment_result.optimal_rotation_deg:.2f}° for optimal mesh")
                else:
                    # Fallback: position without alignment calculation
                    from build123d import Rot, Pos
                    wheel_positioned = wheel
                    worm_positioned = Pos(design.assembly.centre_distance_mm, 0, 0) * Rot(X=90) * worm

                show(wheel_positioned, worm_positioned, names=["wheel", "worm"], colors=["steelblue", "orange"])
            elif wheel is not None:
                show(wheel, names=["wheel"], colors=["steelblue"])
            elif worm is not None:
                show(worm, names=["worm"], colors=["orange"])
            print("Displayed in OCP viewer")

        except ImportError:
            print("\nWarning: ocp_vscode not available for viewing", file=sys.stderr)
            print("Install with: pip install ocp_vscode", file=sys.stderr)

    # Summary
    profile_upper = use_profile
    if profile_upper == "ZK":
        profile_name = "ZK (circular arc, 3D printing)"
    elif profile_upper == "ZI":
        profile_name = "ZI (involute, hobbing)"
    else:
        profile_name = "ZA (straight, CNC)"
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
            worm_type="globoid" if use_globoid else "cylindrical",
            worm_length=use_worm_length,
            wheel_width=use_wheel_width,
            wheel_throated=args.hobbed,
            profile=use_profile,
            worm_features=worm_features,
            wheel_features=wheel_features
        )

        # Create measured geometry from rim thickness results
        measured_geometry = None
        if worm_rim_result is not None or wheel_rim_result is not None:
            from datetime import datetime
            measured_geometry = MeasuredGeometry(
                wheel_rim_thickness_mm=wheel_rim_result.minimum_thickness_mm if wheel_rim_result else None,
                wheel_measurement_point=MeasurementPoint(
                    x_mm=wheel_rim_result.measurement_point_bore[0],
                    y_mm=wheel_rim_result.measurement_point_bore[1],
                    z_mm=wheel_rim_result.measurement_point_bore[2]
                ) if wheel_rim_result and wheel_rim_result.measurement_point_bore else None,
                wheel_rim_warning=wheel_rim_result.has_warning if wheel_rim_result else None,
                worm_rim_thickness_mm=worm_rim_result.minimum_thickness_mm if worm_rim_result else None,
                worm_measurement_point=MeasurementPoint(
                    x_mm=worm_rim_result.measurement_point_bore[0],
                    y_mm=worm_rim_result.measurement_point_bore[1],
                    z_mm=worm_rim_result.measurement_point_bore[2]
                ) if worm_rim_result and worm_rim_result.measurement_point_bore else None,
                worm_rim_warning=worm_rim_result.has_warning if worm_rim_result else None,
                measurement_timestamp=datetime.now().isoformat()
            )

        # Create complete design with manufacturing parameters
        complete_design = WormGearDesign(
            worm=design.worm,
            wheel=design.wheel,
            assembly=design.assembly,
            manufacturing=manufacturing,
            measured_geometry=measured_geometry
        )

        # Save to file
        output_path = Path(args.save_json)
        save_design_json(complete_design, output_path)
        print(f"\nSaved extended JSON: {output_path}")
        print(f"  This JSON includes all manufacturing features and can fully reproduce this design")

    return 0


if __name__ == '__main__':
    sys.exit(main())
