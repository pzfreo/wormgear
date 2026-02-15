#!/usr/bin/env python3
"""Compare two STEP files geometrically with gear-aware interpretation.

Shows what changed in terms meaningful for worm gears: diameters, thread
profiles, bores, and overall envelope — not just raw percentages.

Usage:
    python scripts/compare_step.py reference.step candidate.step
    python scripts/compare_step.py reference.step candidate.step --tolerance 0.1
    python scripts/compare_step.py old_dir/ new_dir/  # compare matching files
"""

import argparse
import sys
from pathlib import Path

from build123d import import_step, Part
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SHELL, TopAbs_SOLID


def count_topology(part: Part) -> dict:
    """Count topological entities (faces, edges, solids, shells)."""
    counts = {}
    for name, kind in [
        ("solids", TopAbs_SOLID),
        ("shells", TopAbs_SHELL),
        ("faces", TopAbs_FACE),
        ("edges", TopAbs_EDGE),
    ]:
        explorer = TopExp_Explorer(part.wrapped, kind)
        n = 0
        while explorer.More():
            n += 1
            explorer.Next()
        counts[name] = n
    return counts


def get_properties(part: Part) -> dict:
    """Extract geometric properties from a Part."""
    # Volume
    vol_props = GProp_GProps()
    BRepGProp.VolumeProperties_s(part.wrapped, vol_props)
    volume = vol_props.Mass()

    # Surface area
    surf_props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(part.wrapped, surf_props)
    surface_area = surf_props.Mass()

    # Centre of mass
    com = vol_props.CentreOfMass()
    centre_of_mass = (com.X(), com.Y(), com.Z())

    # Bounding box
    bbox = Bnd_Box()
    BRepBndLib.Add_s(part.wrapped, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

    # Topology
    topo = count_topology(part)

    return {
        "volume_mm3": volume,
        "surface_area_mm2": surface_area,
        "centre_of_mass": centre_of_mass,
        "bbox_min": (xmin, ymin, zmin),
        "bbox_max": (xmax, ymax, zmax),
        "bbox_size": (xmax - xmin, ymax - ymin, zmax - zmin),
        "is_valid": part.is_valid,
        "topo": topo,
    }


def compare(ref_path: Path, cand_path: Path, tolerance_pct: float) -> dict:
    """Compare two STEP files. Returns dict with comparison results."""
    ref_part = import_step(str(ref_path))
    cand_part = import_step(str(cand_path))

    ref = get_properties(ref_part)
    cand = get_properties(cand_part)

    def pct_diff(a, b):
        if a == 0:
            return 0.0 if b == 0 else float("inf")
        return abs(b - a) / abs(a) * 100

    def abs_diff(a, b):
        return b - a  # signed: positive = candidate is bigger

    vol_diff_pct = pct_diff(ref["volume_mm3"], cand["volume_mm3"])
    area_diff_pct = pct_diff(ref["surface_area_mm2"], cand["surface_area_mm2"])

    vol_diff_mm3 = abs_diff(ref["volume_mm3"], cand["volume_mm3"])
    area_diff_mm2 = abs_diff(ref["surface_area_mm2"], cand["surface_area_mm2"])

    bbox_diffs_mm = tuple(
        abs_diff(r, c) for r, c in zip(ref["bbox_size"], cand["bbox_size"])
    )
    bbox_diffs_pct = []
    for r, c in zip(ref["bbox_size"], cand["bbox_size"]):
        if abs(r) < 0.001:
            bbox_diffs_pct.append(0.0 if abs(c) < 0.001 else float("inf"))
        else:
            bbox_diffs_pct.append(pct_diff(r, c))

    com_dist = sum(
        (a - b) ** 2 for a, b in zip(ref["centre_of_mass"], cand["centre_of_mass"])
    ) ** 0.5

    max_bbox_pct = max(bbox_diffs_pct)

    all_pass = (
        vol_diff_pct <= tolerance_pct
        and area_diff_pct <= tolerance_pct
        and max_bbox_pct <= tolerance_pct
        and ref["is_valid"]
        and cand["is_valid"]
    )

    return {
        "ref": ref,
        "cand": cand,
        "volume_diff_pct": vol_diff_pct,
        "volume_diff_mm3": vol_diff_mm3,
        "surface_area_diff_pct": area_diff_pct,
        "surface_area_diff_mm2": area_diff_mm2,
        "bbox_diffs_mm": bbox_diffs_mm,
        "bbox_diffs_pct": bbox_diffs_pct,
        "com_distance_mm": com_dist,
        "pass": all_pass,
    }


def interpret_changes(result: dict) -> list[str]:
    """Infer what likely changed based on the geometric diffs."""
    notes = []
    ref = result["ref"]
    cand = result["cand"]

    vol_d = result["volume_diff_mm3"]
    area_d = result["surface_area_diff_mm2"]
    bbox_d = result["bbox_diffs_mm"]

    vol_pct = result["volume_diff_pct"]
    area_pct = result["surface_area_diff_pct"]

    face_diff = cand["topo"]["faces"] - ref["topo"]["faces"]
    edge_diff = cand["topo"]["edges"] - ref["topo"]["edges"]

    # Everything identical
    if vol_pct < 0.001 and area_pct < 0.001 and max(abs(d) for d in bbox_d) < 0.001:
        notes.append("Geometrically identical")
        return notes

    # Bore added or removed (volume decreases, area increases, bbox unchanged)
    envelope_unchanged = all(abs(d) < 0.01 for d in bbox_d)
    if envelope_unchanged and vol_d < -1.0 and area_d > 0:
        notes.append(
            f"Likely bore/pocket ADDED (volume -{abs(vol_d):.1f} mm3, "
            f"area +{area_d:.1f} mm2, envelope unchanged)"
        )
    elif envelope_unchanged and vol_d > 1.0 and area_d < 0:
        notes.append(
            f"Likely bore/pocket REMOVED (volume +{vol_d:.1f} mm3, "
            f"area {area_d:.1f} mm2, envelope unchanged)"
        )

    # Diameter change (bbox X or Y changed, Z unchanged for worm)
    xy_max = max(abs(bbox_d[0]), abs(bbox_d[1]))
    z_change = abs(bbox_d[2])
    if xy_max > 0.01:
        direction = "larger" if max(bbox_d[0], bbox_d[1]) > 0 else "smaller"
        notes.append(
            f"Radial envelope changed by {xy_max:+.3f} mm ({direction} diameter)"
        )

    # Length change (bbox Z changed)
    if z_change > 0.01:
        direction = "longer" if bbox_d[2] > 0 else "shorter"
        notes.append(f"Axial length changed by {bbox_d[2]:+.3f} mm ({direction})")

    # Thread profile / tooth shape change (face count changed, volume changed,
    # but envelope roughly same)
    if face_diff != 0 and envelope_unchanged:
        notes.append(
            f"Topology changed ({face_diff:+d} faces, {edge_diff:+d} edges) "
            f"— likely thread/tooth profile change"
        )
    elif face_diff != 0:
        notes.append(f"Topology changed ({face_diff:+d} faces, {edge_diff:+d} edges)")

    # Surface quality change (area changed but volume and bbox didn't)
    if (
        area_pct > 0.1
        and vol_pct < 0.05
        and envelope_unchanged
        and not any("bore" in n.lower() for n in notes)
    ):
        notes.append(
            f"Surface area changed by {area_d:+.1f} mm2 with minimal volume change "
            f"— likely mesh resolution or surface smoothness difference"
        )

    # Centre of mass shift
    if result["com_distance_mm"] > 0.01:
        notes.append(
            f"Centre of mass shifted by {result['com_distance_mm']:.3f} mm"
        )

    # Volume-only change (no envelope or topo change)
    if (
        vol_pct > 0.05
        and envelope_unchanged
        and face_diff == 0
        and not notes
    ):
        notes.append(
            f"Volume changed by {vol_d:+.1f} mm3 ({vol_pct:.2f}%) "
            f"with same topology — possible clearance/backlash adjustment"
        )

    if not notes:
        notes.append("Minor numerical differences only")

    return notes


def print_report(name: str, result: dict, tolerance_pct: float):
    """Print comparison report for one file pair."""
    ref = result["ref"]
    cand = result["cand"]

    status = "PASS" if result["pass"] else "FAIL"
    print(f"\n{'=' * 70}")
    print(f"  {name}: {status}")
    print(f"{'=' * 70}")

    def metric(label, ref_val, cand_val, diff_pct, diff_abs, unit="", abs_unit=""):
        marker = " " if diff_pct <= tolerance_pct else "!"
        sign = "+" if diff_abs > 0 else ""
        print(
            f"  {marker} {label:.<24s} "
            f"ref={ref_val:>10.3f}{unit}  "
            f"new={cand_val:>10.3f}{unit}  "
            f"{sign}{diff_abs:.3f}{abs_unit}  "
            f"({diff_pct:.3f}%)"
        )

    # --- Dimensions ---
    print(f"  Dimensions:")
    bx, cx = ref["bbox_size"], cand["bbox_size"]
    bd, bp = result["bbox_diffs_mm"], result["bbox_diffs_pct"]
    for i, axis in enumerate(("X (width)", "Y (height)", "Z (length)")):
        metric(f"  {axis}", bx[i], cx[i], bp[i], bd[i], " mm", " mm")

    # --- Volume & Area ---
    print(f"  Material:")
    metric(
        "  Volume", ref["volume_mm3"], cand["volume_mm3"],
        result["volume_diff_pct"], result["volume_diff_mm3"], " mm3", " mm3",
    )
    metric(
        "  Surface area", ref["surface_area_mm2"], cand["surface_area_mm2"],
        result["surface_area_diff_pct"], result["surface_area_diff_mm2"], " mm2", " mm2",
    )

    # --- Topology ---
    rt, ct = ref["topo"], cand["topo"]
    if rt != ct:
        print(f"  Topology:")
        for key in ("faces", "edges"):
            diff = ct[key] - rt[key]
            marker = " " if diff == 0 else "*"
            print(f"  {marker}   {key:.<24s} ref={rt[key]:>5d}       new={ct[key]:>5d}       {diff:+d}")
    else:
        print(f"  Topology: identical ({rt['faces']} faces, {rt['edges']} edges)")

    # --- Position ---
    print(f"  Position:")
    print(f"      Centre of mass shift: {result['com_distance_mm']:.4f} mm")
    print(f"      Validity: ref={ref['is_valid']}, new={cand['is_valid']}")

    # --- Interpretation ---
    notes = interpret_changes(result)
    print(f"  Interpretation:")
    for note in notes:
        print(f"    -> {note}")

    print(f"  Tolerance: {tolerance_pct}%")


def main():
    parser = argparse.ArgumentParser(
        description="Compare STEP files with gear-aware geometric analysis."
    )
    parser.add_argument("reference", help="Reference STEP file or directory")
    parser.add_argument("candidate", help="Candidate STEP file or directory to compare")
    parser.add_argument(
        "--tolerance", "-t", type=float, default=1.0,
        help="Max allowed difference in %% (default: 1.0%%)",
    )
    args = parser.parse_args()

    ref_path = Path(args.reference)
    cand_path = Path(args.candidate)

    pairs = []

    if ref_path.is_file() and cand_path.is_file():
        pairs.append((ref_path.name, ref_path, cand_path))
    elif ref_path.is_dir() and cand_path.is_dir():
        ref_files = sorted(ref_path.glob("*.step")) + sorted(ref_path.glob("*.STEP"))
        for rf in ref_files:
            cf = cand_path / rf.name
            if cf.exists():
                pairs.append((rf.name, rf, cf))
            else:
                print(f"  SKIP {rf.name} (no match in {cand_path})")
        if not pairs:
            print(f"No matching STEP files found between {ref_path} and {cand_path}")
            sys.exit(1)
    else:
        print("Error: both arguments must be files or both must be directories")
        sys.exit(1)

    results = []
    for name, rf, cf in pairs:
        result = compare(rf, cf, args.tolerance)
        results.append((name, result))
        print_report(name, result, args.tolerance)

    all_pass = all(r["pass"] for _, r in results)

    print(f"\n{'=' * 70}")
    if all_pass:
        print(f"  ALL {len(results)} file(s) PASS (within {args.tolerance}% tolerance)")
    else:
        failures = sum(1 for _, r in results if not r["pass"])
        print(f"  {failures}/{len(results)} file(s) FAILED (exceeded {args.tolerance}% tolerance)")
    print(f"{'=' * 70}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
