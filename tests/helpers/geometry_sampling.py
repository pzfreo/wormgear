"""
Cross-section sampling and measurement utilities for worm geometry verification.

Slices worm solids at given Z positions and measures thread profile dimensions
(tip/root radii, thread thickness, lead, flank angles) for comparing against
design parameters.
"""

import math
from typing import List, Tuple, Optional

from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Ax3, gp_Ax1, gp_Ax2
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.BRep import BRep_Tool
from OCP.GCPnts import GCPnts_UniformAbscissa
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GeomAPI import GeomAPI_IntCS
from OCP.Geom import Geom_Plane
from OCP.TopoDS import TopoDS


def _sample_edges_at_z(solid, z: float) -> List[Tuple[float, float]]:
    """
    Slice a solid with an XY plane at the given Z and return (x, y) points
    sampled along all resulting edges.
    """
    shape = solid.wrapped if hasattr(solid, 'wrapped') else solid

    # Create section plane at Z
    plane = gp_Pln(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1))
    section = BRepAlgoAPI_Section(shape, plane)
    section.Build()

    if not section.IsDone():
        return []

    section_shape = section.Shape()

    # Sample points from all edges in the section
    points = []
    explorer = TopExp_Explorer(section_shape, TopAbs_EDGE)
    while explorer.More():
        edge = TopoDS.Edge_s(explorer.Current())
        curve = BRepAdaptor_Curve(edge)
        # Sample each edge at many points
        n_samples = 50
        u_start = curve.FirstParameter()
        u_end = curve.LastParameter()
        for i in range(n_samples + 1):
            u = u_start + (u_end - u_start) * i / n_samples
            pt = curve.Value(u)
            points.append((pt.X(), pt.Y()))
        explorer.Next()

    return points


def measure_radial_profile(solid, z: float) -> dict:
    """
    Measure radial profile at a given Z coordinate.

    Slices the worm solid with an XY plane and analyzes the resulting
    cross-section to extract:
    - max_radius: maximum distance from axis (tip radius)
    - min_radius: minimum distance from axis in thread region (root radius)
    - radii_at_angles: radius measurements at regular angular intervals

    Returns dict with profile measurements.
    """
    points = _sample_edges_at_z(solid, z)
    if not points:
        return {"max_radius": 0, "min_radius": 0, "points": []}

    # Calculate radii from axis
    radii = []
    for x, y in points:
        r = math.sqrt(x * x + y * y)
        angle = math.atan2(y, x)
        radii.append((angle, r))

    if not radii:
        return {"max_radius": 0, "min_radius": 0, "points": []}

    all_r = [r for _, r in radii]

    return {
        "max_radius": max(all_r),
        "min_radius": min(all_r),
        "points": radii,
    }


def measure_thread_at_angle(solid, z: float, angle_deg: float,
                            pitch_radius: float) -> dict:
    """
    Measure thread profile along a radial line at a given angle.

    Intersects the worm cross-section at Z with a radial line at angle_deg
    to find thread boundaries. Returns the thread's radial extents and width.

    Args:
        solid: Worm solid
        z: Z coordinate to slice at
        angle_deg: Angle in degrees from X axis for the radial measurement
        pitch_radius: Expected pitch radius for reference

    Returns dict with:
        tip_radius: outermost intersection radius
        root_radius: innermost intersection radius in thread
        thread_found: bool indicating if a thread was found at this angle
    """
    points = _sample_edges_at_z(solid, z)
    if not points:
        return {"tip_radius": 0, "root_radius": 0, "thread_found": False}

    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Find points near this radial line (within angular tolerance)
    angular_tol = math.radians(3.0)  # 3 degree tolerance band
    nearby_radii = []
    for x, y in points:
        r = math.sqrt(x * x + y * y)
        if r < 0.1:
            continue
        pt_angle = math.atan2(y, x)
        angle_diff = abs(pt_angle - angle_rad)
        # Handle wraparound
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        if angle_diff < angular_tol:
            nearby_radii.append(r)

    if not nearby_radii:
        return {"tip_radius": 0, "root_radius": 0, "thread_found": False}

    return {
        "tip_radius": max(nearby_radii),
        "root_radius": min(nearby_radii),
        "thread_found": True,
    }


def measure_thread_thickness_at_z(solid, z: float, pitch_radius: float,
                                  num_starts: int = 1) -> Optional[float]:
    """
    Measure thread thickness (axial width at pitch radius) from cross-section.

    Samples points at the pitch radius and measures the angular extent of
    each thread tooth, converting to axial thickness.

    Args:
        solid: Worm solid
        z: Z coordinate to slice at
        pitch_radius: Pitch radius to measure at
        num_starts: Number of worm starts

    Returns:
        Average thread angular extent in degrees, or None if measurement fails.
    """
    points = _sample_edges_at_z(solid, z)
    if not points:
        return None

    # Find points near the pitch radius
    r_tol = pitch_radius * 0.15  # 15% tolerance band around pitch radius
    pitch_points_angles = []
    for x, y in points:
        r = math.sqrt(x * x + y * y)
        if abs(r - pitch_radius) < r_tol:
            angle = math.atan2(y, x)
            pitch_points_angles.append(angle)

    if len(pitch_points_angles) < 4:
        return None

    # Sort by angle to find thread extents
    pitch_points_angles.sort()

    # Find gaps (spaces between threads) and teeth (thread arcs)
    # A gap larger than the expected tooth spacing indicates a space
    # Expected tooth extent for one start: ~thread_thickness / (pi * pitch_diameter) * 360
    # We'll just measure the angular clusters

    # Group nearby angles into clusters (threads)
    clusters = []
    current_cluster = [pitch_points_angles[0]]

    for i in range(1, len(pitch_points_angles)):
        gap = pitch_points_angles[i] - pitch_points_angles[i - 1]
        if gap < math.radians(5.0):  # Within 5 degrees = same cluster
            current_cluster.append(pitch_points_angles[i])
        else:
            if len(current_cluster) >= 2:
                clusters.append(current_cluster)
            current_cluster = [pitch_points_angles[i]]

    # Check wraparound - last cluster might connect to first
    if len(current_cluster) >= 2:
        if clusters and (2 * math.pi - pitch_points_angles[-1] + pitch_points_angles[0]) < math.radians(5.0):
            clusters[0] = current_cluster + clusters[0]
        else:
            clusters.append(current_cluster)

    if not clusters:
        return None

    # Measure angular extent of each thread cluster
    extents = []
    for cluster in clusters:
        extent = max(cluster) - min(cluster)
        extents.append(math.degrees(extent))

    return sum(extents) / len(extents) if extents else None


def _cluster_tip_angles(tip_points: List[Tuple[float, float]],
                        min_gap_rad: float = 0.3) -> List[float]:
    """
    Cluster tip points by angular proximity, return mean angle of each cluster.

    For a multi-start worm, there are N tip regions per cross-section.  We group
    nearby points into clusters and return the mean angle of each cluster.
    """
    if not tip_points:
        return []

    # Sort by angle
    angles = sorted(a for a, _ in tip_points)

    clusters: List[List[float]] = [[angles[0]]]
    for a in angles[1:]:
        if a - clusters[-1][-1] < min_gap_rad:
            clusters[-1].append(a)
        else:
            clusters.append([a])

    # Check wraparound: first and last cluster may be the same thread
    if len(clusters) > 1:
        wrap_gap = (2 * math.pi) - clusters[-1][-1] + clusters[0][0]
        if wrap_gap < min_gap_rad:
            clusters[0] = clusters[-1] + clusters[0]
            clusters.pop()

    # Mean angle of each cluster (circular mean)
    means = []
    for cluster in clusters:
        sc = sum(math.cos(a) for a in cluster)
        ss = sum(math.sin(a) for a in cluster)
        means.append(math.atan2(ss, sc))
    return means


def measure_lead(solid, pitch_radius: float, worm_length: float) -> Optional[float]:
    """
    Measure the actual lead by tracking one thread's angular progression
    along the Z axis.

    At each Z slice, finds all thread-tip clusters (one per start) and
    follows the cluster nearest to the previous measurement, so multi-start
    worms are handled correctly.

    Args:
        solid: Worm solid
        pitch_radius: Expected pitch radius
        worm_length: Total worm length (to set Z scan range)

    Returns:
        Measured lead in mm, or None if measurement fails.
    """
    half_length = worm_length / 2
    n_slices = 60
    z_values = []
    peak_angles = []
    prev_angle = None

    for i in range(n_slices):
        z = -half_length * 0.8 + (half_length * 1.6) * i / (n_slices - 1)
        profile = measure_radial_profile(solid, z)

        if profile["max_radius"] < pitch_radius * 0.5:
            continue

        if not profile["points"]:
            continue

        max_r = profile["max_radius"]
        tip_points = [(a, r) for a, r in profile["points"]
                      if r > max_r * 0.95]

        if not tip_points:
            continue

        cluster_means = _cluster_tip_angles(tip_points)
        if not cluster_means:
            continue

        if prev_angle is None:
            # First slice — pick the cluster closest to 0
            chosen = min(cluster_means, key=lambda a: abs(a))
        else:
            # Pick the cluster nearest to the previous angle (track one thread)
            def _angle_dist(a):
                d = a - prev_angle
                while d > math.pi:
                    d -= 2 * math.pi
                while d < -math.pi:
                    d += 2 * math.pi
                return abs(d)
            chosen = min(cluster_means, key=_angle_dist)

        prev_angle = chosen
        z_values.append(z)
        peak_angles.append(chosen)

    if len(z_values) < 10:
        return None

    # Unwrap angles (remove 2*pi jumps)
    unwrapped = [peak_angles[0]]
    for i in range(1, len(peak_angles)):
        diff = peak_angles[i] - peak_angles[i - 1]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        unwrapped.append(unwrapped[-1] + diff)

    # Linear fit: angle = slope * z + intercept
    # slope = d(angle)/dz, lead = 2*pi / abs(slope)
    n = len(z_values)
    sum_z = sum(z_values)
    sum_a = sum(unwrapped)
    sum_za = sum(z * a for z, a in zip(z_values, unwrapped))
    sum_zz = sum(z * z for z in z_values)

    denom = n * sum_zz - sum_z * sum_z
    if abs(denom) < 1e-12:
        return None

    slope = (n * sum_za - sum_z * sum_a) / denom

    if abs(slope) < 1e-6:
        return None

    lead = 2 * math.pi / abs(slope)
    return lead


def measure_flank_angle(solid, z: float, pitch_radius: float,
                        addendum: float, dedendum: float) -> Optional[float]:
    """
    Measure the flank angle of the thread profile at a given Z.

    For ZA profiles, the flank should be a straight line at the pressure angle.
    Measures the angle by sampling the thread boundary at different radii.

    Args:
        solid: Worm solid
        z: Z coordinate to slice at
        pitch_radius: Pitch radius
        addendum: Expected addendum
        dedendum: Expected dedendum

    Returns:
        Measured flank angle in degrees, or None if measurement fails.
    """
    points = _sample_edges_at_z(solid, z)
    if not points:
        return None

    # Convert to polar
    polar = []
    for x, y in points:
        r = math.sqrt(x * x + y * y)
        angle = math.atan2(y, x)
        polar.append((angle, r))

    # Find a thread tooth - look for the angular region with large radii
    # Sort by angle
    polar.sort(key=lambda p: p[0])

    # Find a peak (thread tip region)
    max_r = max(r for _, r in polar)
    tip_threshold = pitch_radius + addendum * 0.5

    # Find a contiguous region above pitch radius (a tooth)
    in_tooth = False
    tooth_points = []
    best_tooth = []

    for angle, r in polar:
        if r > tip_threshold:
            if not in_tooth:
                in_tooth = True
                tooth_points = []
            tooth_points.append((angle, r))
        else:
            if in_tooth:
                if len(tooth_points) > len(best_tooth):
                    best_tooth = tooth_points[:]
                in_tooth = False

    if in_tooth and len(tooth_points) > len(best_tooth):
        best_tooth = tooth_points

    if len(best_tooth) < 5:
        return None

    # The tooth profile in (angle, r) space shows the flank angle
    # At pitch radius, the angular width is the thread thickness
    # The flank angle is related to how the angular width changes with radius

    # Sample the leading edge of the tooth at different radii
    # Sort tooth points by radius
    best_tooth.sort(key=lambda p: p[1])

    # Get the minimum angle at each radius level (leading flank)
    root_r = pitch_radius - dedendum * 0.5
    tip_r = pitch_radius + addendum * 0.5

    # Filter to the radial range of interest
    flank_points = [(a, r) for a, r in best_tooth
                    if root_r < r < tip_r]

    if len(flank_points) < 3:
        return None

    # For each radius, find the edge (minimum angle = one flank)
    # Bin by radius
    n_bins = 5
    r_range = tip_r - root_r
    bins = [[] for _ in range(n_bins)]
    for a, r in flank_points:
        bin_idx = min(n_bins - 1, int((r - root_r) / r_range * n_bins))
        bins[bin_idx].append((a, r))

    edge_points = []
    for bin_pts in bins:
        if bin_pts:
            # Take the minimum angle point (one flank edge)
            min_pt = min(bin_pts, key=lambda p: p[0])
            edge_points.append(min_pt)

    if len(edge_points) < 2:
        return None

    # Convert angular difference to axial-like measurement
    # At radius r, angular change da corresponds to linear distance r*da
    # The flank angle is atan(linear_width_change / radial_change)
    # = atan(r * d_angle / d_r)

    # Linear fit of angle vs radius for the flank
    angles = [a for a, r in edge_points]
    radii = [r for a, r in edge_points]

    n = len(radii)
    mean_r = sum(radii) / n
    mean_a = sum(angles) / n
    num = sum((r - mean_r) * (a - mean_a) for r, a in zip(radii, angles))
    den = sum((r - mean_r) ** 2 for r in radii)

    if abs(den) < 1e-12:
        return None

    da_dr = num / den  # change in angle per unit radius

    # Convert to flank angle: at the pitch radius
    # Linear displacement = pitch_radius * da (for small da per unit dr)
    linear_slope = pitch_radius * abs(da_dr)
    flank_angle_deg = math.degrees(math.atan(linear_slope))

    return flank_angle_deg
