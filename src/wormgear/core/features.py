"""
Bore and keyway feature generation for worm gear components.

Supports:
- Center bores (through holes)
- Keyways per DIN 6885 / ISO 6885 standard
- Set screw holes for shaft retention
- Hub options for wheel mounting (flush, extended, flanged)
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple
from build123d import (
    Part, Cylinder, Box, Align, Axis, Location, Pos,
)

# Import bore calculation (pure geometry math)
from .bore_sizing import calculate_default_bore


# DIN 6885 Keyway dimensions lookup table
# Format: bore_range: (key_width, key_height, shaft_depth, hub_depth)
# bore_range is (min_bore, max_bore) in mm
DIN_6885_KEYWAYS = {
    (6, 8): (2, 2, 1.2, 1.0),
    (8, 10): (3, 3, 1.8, 1.4),
    (10, 12): (4, 4, 2.5, 1.8),
    (12, 17): (5, 5, 3.0, 2.3),
    (17, 22): (6, 6, 3.5, 2.8),
    (22, 30): (8, 7, 4.0, 3.3),
    (30, 38): (10, 8, 5.0, 3.3),
    (38, 44): (12, 8, 5.0, 3.3),
    (44, 50): (14, 9, 5.5, 3.8),
    (50, 58): (16, 10, 6.0, 4.3),
    (58, 65): (18, 11, 7.0, 4.4),
    (65, 75): (20, 12, 7.5, 4.9),
    (75, 85): (22, 14, 9.0, 5.4),
    (85, 95): (25, 14, 9.0, 5.4),
}


# Set screw sizing based on bore diameter
# Format: bore_range: (screw_size_name, thread_diameter_mm)
# Common sizes: M2 (2mm), M3 (3mm), M4 (4mm), M5 (5mm), M6 (6mm)
SET_SCREW_SIZES = {
    (2, 6): ("M2", 2.0),      # Very small bores (below DIN 6885 range)
    (6, 10): ("M3", 3.0),     # Small bores
    (10, 20): ("M4", 4.0),    # Medium bores
    (20, 35): ("M5", 5.0),    # Large bores
    (35, 60): ("M6", 6.0),    # Very large bores
    (60, 100): ("M8", 8.0),   # Extra large bores
}



def get_din_6885_keyway(bore_diameter: float) -> Optional[Tuple[float, float, float, float]]:
    """
    Look up DIN 6885 keyway dimensions for a given bore diameter.

    Args:
        bore_diameter: Bore diameter in mm

    Returns:
        Tuple of (key_width, key_height, shaft_depth, hub_depth) in mm,
        or None if bore is outside standard range
    """
    for (min_d, max_d), dims in DIN_6885_KEYWAYS.items():
        if min_d <= bore_diameter < max_d:
            return dims
    return None


def get_set_screw_size(bore_diameter: float) -> Tuple[str, float]:
    """
    Determine appropriate set screw size based on bore diameter.

    Args:
        bore_diameter: Bore diameter in mm

    Returns:
        Tuple of (size_name, thread_diameter) in mm (e.g., ("M4", 4.0))

    Raises:
        ValueError: If bore is too small for set screws
    """
    if bore_diameter < 2.0:
        raise ValueError(
            f"Bore diameter {bore_diameter}mm is too small for set screws (min 2mm)"
        )

    for (min_d, max_d), (name, diameter) in SET_SCREW_SIZES.items():
        if min_d <= bore_diameter < max_d:
            return (name, diameter)

    # For bores larger than table, use M8
    return ("M8", 8.0)


@dataclass
class BoreFeature:
    """
    Bore (center hole) feature specification.

    Attributes:
        diameter: Bore diameter in mm
        through: If True, bore goes all the way through (default)
        depth: If not through, depth of bore in mm
    """
    diameter: float
    through: bool = True
    depth: Optional[float] = None

    def __post_init__(self):
        if self.diameter <= 0:
            raise ValueError(f"Bore diameter must be positive, got {self.diameter}")
        if not self.through and self.depth is None:
            raise ValueError("Non-through bore requires depth specification")
        if self.depth is not None and self.depth <= 0:
            raise ValueError(f"Bore depth must be positive, got {self.depth}")


@dataclass
class KeywayFeature:
    """
    Keyway feature specification per DIN 6885 / ISO 6885.

    If width and depth are not specified, they are auto-calculated from
    the bore diameter using DIN 6885 standard dimensions.

    Attributes:
        width: Key width in mm (auto from bore if None)
        depth: Keyway depth in mm (auto from bore if None)
        length: Keyway length in mm (full length if None)
        is_shaft: True for shaft keyway (worm), False for hub keyway (wheel)
    """
    width: Optional[float] = None
    depth: Optional[float] = None
    length: Optional[float] = None
    is_shaft: bool = False  # False = hub (wheel), True = shaft (worm)

    def get_dimensions(self, bore_diameter: float) -> Tuple[float, float]:
        """
        Get keyway width and depth, using DIN 6885 if not specified.

        Args:
            bore_diameter: Bore diameter in mm

        Returns:
            Tuple of (width, depth) in mm

        Raises:
            ValueError: If bore is outside DIN 6885 range and dimensions not specified
        """
        if self.width is not None and self.depth is not None:
            return (self.width, self.depth)

        # Look up standard dimensions
        dims = get_din_6885_keyway(bore_diameter)
        if dims is None:
            raise ValueError(
                f"Bore diameter {bore_diameter}mm is outside DIN 6885 range (6-95mm). "
                "Please specify keyway width and depth manually."
            )

        key_width, key_height, shaft_depth, hub_depth = dims

        width = self.width if self.width is not None else key_width
        if self.depth is not None:
            depth = self.depth
        else:
            depth = shaft_depth if self.is_shaft else hub_depth

        return (width, depth)


@dataclass
class SetScrewFeature:
    """
    Set screw hole feature specification for shaft retention.

    Set screws are threaded holes drilled radially through the bore wall,
    allowing grub screws to secure the gear to a shaft.

    If size is not specified, it is auto-calculated from the bore diameter.

    Attributes:
        size: Screw size name (e.g., "M3", "M4") - auto-sized if None
        diameter: Thread diameter in mm - auto-sized if None
        count: Number of set screws (1-3, default: 1)
        angular_offset: Starting angle in degrees (0 = aligned with +X axis)
                       For parts with keyways, screws are automatically positioned
                       90° from keyway to avoid interference
    """
    size: Optional[str] = None
    diameter: Optional[float] = None
    count: int = 1
    angular_offset: float = 90.0  # Default: 90° from keyway (top position)

    def __post_init__(self):
        if self.count < 1 or self.count > 3:
            raise ValueError(f"Set screw count must be 1-3, got {self.count}")
        if self.diameter is not None and self.diameter <= 0:
            raise ValueError(f"Set screw diameter must be positive, got {self.diameter}")

    def get_screw_specs(self, bore_diameter: float) -> Tuple[str, float]:
        """
        Get set screw size and diameter, auto-sizing if not specified.

        Args:
            bore_diameter: Bore diameter in mm

        Returns:
            Tuple of (size_name, thread_diameter) in mm
        """
        if self.size is not None and self.diameter is not None:
            return (self.size, self.diameter)

        # Auto-size from bore
        auto_size, auto_diameter = get_set_screw_size(bore_diameter)

        size = self.size if self.size is not None else auto_size
        diameter = self.diameter if self.diameter is not None else auto_diameter

        return (size, diameter)


@dataclass
class HubFeature:
    """
    Hub feature specification for wheel mounting.

    Hubs provide mounting surface and positioning for the wheel. Three types:
    - flush: Hub face is flush with wheel face (default, no extension)
    - extended: Hub extends beyond wheel face for bearing support
    - flanged: Extended hub with larger diameter flange and bolt holes

    Attributes:
        hub_type: Type of hub - "flush", "extended", or "flanged"
        length: Hub extension length in mm (for extended/flanged, default: 10mm)
        flange_diameter: Outer diameter of flange in mm (for flanged only)
        flange_thickness: Thickness of flange in mm (for flanged, default: 5mm)
        bolt_holes: Number of bolt holes in flange (for flanged, 0-8, default: 4)
        bolt_diameter: Bolt hole diameter in mm (for flanged, default: auto from wheel)
    """
    hub_type: str = "flush"
    length: Optional[float] = None
    flange_diameter: Optional[float] = None
    flange_thickness: Optional[float] = None
    bolt_holes: int = 4
    bolt_diameter: Optional[float] = None

    def __post_init__(self):
        valid_types = ["flush", "extended", "flanged"]
        if self.hub_type not in valid_types:
            raise ValueError(
                f"Hub type must be one of {valid_types}, got '{self.hub_type}'"
            )

        if self.hub_type in ["extended", "flanged"]:
            if self.length is None:
                self.length = 10.0  # Default 10mm extension
            elif self.length <= 0:
                raise ValueError(f"Hub length must be positive, got {self.length}")

        if self.hub_type == "flanged":
            if self.flange_thickness is None:
                self.flange_thickness = 5.0  # Default 5mm flange
            elif self.flange_thickness <= 0:
                raise ValueError(
                    f"Flange thickness must be positive, got {self.flange_thickness}"
                )

            if self.bolt_holes < 0 or self.bolt_holes > 8:
                raise ValueError(
                    f"Bolt holes must be 0-8, got {self.bolt_holes}"
                )

            # Flange diameter will be validated when we know wheel size


@dataclass
class DDCutFeature:
    """
    Double-D cut feature specification for small diameter anti-rotation.

    A double-D (D-D) shaft has two parallel flats on opposite sides,
    creating a D-shaped cross-section when viewed from two perpendicular angles.
    This provides excellent anti-rotation for small shafts where keyways are
    impractical or too weak (typically below 6mm diameter).

    The flat depth can be specified either as:
    - depth: Direct depth of flat cut from bore surface (in mm)
    - flat_to_flat: Distance between the two parallel flats (in mm)

    Standard practice for small shafts:
    - 3mm bore: 0.3mm depth or 2.4mm flat-to-flat
    - 4mm bore: 0.4mm depth or 3.2mm flat-to-flat
    - 5mm bore: 0.4mm depth or 4.2mm flat-to-flat
    - 6mm bore: 0.5mm depth or 5.0mm flat-to-flat

    Attributes:
        depth: Depth of flat cut from bore surface in mm (mutually exclusive with flat_to_flat)
        flat_to_flat: Distance between parallel flats in mm (mutually exclusive with depth)
        angular_offset: Rotation of first flat in degrees (0 = aligned with +X axis)
    """
    depth: Optional[float] = None
    flat_to_flat: Optional[float] = None
    angular_offset: float = 0.0

    def __post_init__(self):
        if self.depth is None and self.flat_to_flat is None:
            raise ValueError("Must specify either 'depth' or 'flat_to_flat'")

        if self.depth is not None and self.flat_to_flat is not None:
            raise ValueError("Cannot specify both 'depth' and 'flat_to_flat' - choose one")

        if self.depth is not None and self.depth <= 0:
            raise ValueError(f"DD-cut depth must be positive, got {self.depth}")

        if self.flat_to_flat is not None and self.flat_to_flat <= 0:
            raise ValueError(f"DD-cut flat_to_flat must be positive, got {self.flat_to_flat}")

    def get_depth(self, bore_diameter: float) -> float:
        """
        Get the flat cut depth given the bore diameter.

        Args:
            bore_diameter: Bore diameter in mm

        Returns:
            Depth of flat cut from bore surface in mm

        Raises:
            ValueError: If resulting depth is invalid for the bore diameter
        """
        if self.depth is not None:
            depth = self.depth
            # Validate that explicitly specified depth is reasonable
            if depth <= 0:
                raise ValueError(f"DD-cut depth must be positive, got {depth}mm")
            if depth >= bore_diameter / 2:
                raise ValueError(
                    f"DD-cut depth {depth}mm is too large for bore diameter "
                    f"{bore_diameter}mm (max: {bore_diameter/2:.2f}mm)"
                )
            return depth

        # Calculate depth from flat-to-flat dimension
        # flat_to_flat = bore_diameter - 2*depth
        # depth = (bore_diameter - flat_to_flat) / 2
        depth = (bore_diameter - self.flat_to_flat) / 2

        if depth <= 0:
            raise ValueError(
                f"flat_to_flat {self.flat_to_flat}mm is too large for "
                f"bore diameter {bore_diameter}mm (would result in negative depth)"
            )

        if depth >= bore_diameter / 2:
            raise ValueError(
                f"flat_to_flat {self.flat_to_flat}mm is too small for "
                f"bore diameter {bore_diameter}mm (would result in no bore)"
            )

        return depth


def calculate_default_ddcut(bore_diameter: float, depth_percent: float = 15.0) -> DDCutFeature:
    """
    Calculate sensible default DD-cut dimensions for a given bore diameter.

    Standard practice: depth ≈ 0.15 × bore_diameter (gives ~70% flat-to-flat ratio).
    This matches common small servo/stepper motor shaft standards.

    Args:
        bore_diameter: Bore diameter in mm
        depth_percent: Depth as percentage of bore diameter (default: 15.0 for ~70% flat-to-flat)
                      Common values: 10% (80% f-t-f), 15% (70% f-t-f), 20% (60% f-t-f)

    Returns:
        DDCutFeature with appropriate dimensions

    Examples:
        >>> calculate_default_ddcut(3.0)
        DDCutFeature(depth=0.5, ...)  # 3mm bore, 0.45mm depth, 2.1mm flat-to-flat (70%)
        >>> calculate_default_ddcut(3.0, depth_percent=10.0)
        DDCutFeature(depth=0.3, ...)  # 3mm bore, 0.3mm depth, 2.4mm flat-to-flat (80%)
    """
    # Calculate depth from percentage
    depth = bore_diameter * (depth_percent / 100.0)

    # Round to nearest 0.1mm
    depth = round(depth * 10) / 10

    # Clamp to reasonable range (5-25% of diameter)
    min_depth = max(0.2, bore_diameter * 0.05)
    max_depth = bore_diameter * 0.25
    depth = max(min_depth, min(depth, max_depth))

    return DDCutFeature(depth=depth)


def create_bore(
    part: Part,
    bore: BoreFeature,
    part_length: float,
    axis: Axis = Axis.Z
) -> Part:
    """
    Create a bore (center hole) in a part.

    Args:
        part: The part to add bore to
        bore: Bore specification
        part_length: Length of the part along bore axis (for through holes)
        axis: Axis along which to create bore (default: Z)

    Returns:
        Part with bore cut
    """
    bore_radius = bore.diameter / 2

    if bore.through:
        # Through bore - extend slightly beyond part
        bore_depth = part_length + 1.0
    else:
        bore_depth = bore.depth

    # Create bore cylinder
    bore_cyl = Cylinder(
        radius=bore_radius,
        height=bore_depth,
        align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )

    # Rotate to correct axis if needed
    if axis == Axis.X:
        bore_cyl = bore_cyl.rotate(Axis.Y, 90)
    elif axis == Axis.Y:
        bore_cyl = bore_cyl.rotate(Axis.X, 90)
    # Z axis is default, no rotation needed

    # Subtract from part
    result = part - bore_cyl

    return result


def create_keyway(
    part: Part,
    bore: BoreFeature,
    keyway: KeywayFeature,
    part_length: float,
    axis: Axis = Axis.Z
) -> Part:
    """
    Create a keyway in a part (requires bore to already exist or be specified).

    For hub keyways (wheel): The slot is cut into the hub material around the bore.
    The depth (t2) is measured radially outward from the bore surface.

    For shaft keyways (worm): The slot is cut into the shaft.
    The depth (t1) is measured radially inward from the shaft outer surface.
    Note: For a shaft with a bore, the keyway is cut from the outer surface inward.

    Args:
        part: The part to add keyway to
        bore: Bore specification (keyway is relative to bore)
        keyway: Keyway specification
        part_length: Length of the part along axis
        axis: Axis along which keyway runs (default: Z)

    Returns:
        Part with keyway cut
    """
    bore_radius = bore.diameter / 2
    width, depth = keyway.get_dimensions(bore.diameter)

    # Keyway length - use full length if not specified
    if keyway.length is not None:
        kw_length = keyway.length
    else:
        kw_length = part_length

    if keyway.is_shaft:
        # Shaft keyway (worm): cut from center axis outward
        # The keyway slot sits at the bore surface and extends outward by 'depth'
        # But since we have a bore hole, we need to create a slot that goes
        # from the center through the bore and into the shaft material by 'depth'
        #
        # DIN 6885 t1 is measured from the shaft surface, so the bottom of the
        # keyway is at radius = bore_radius + depth
        keyway_box = Box(
            bore_radius + depth,  # from center to (bore_radius + depth)
            width,  # tangential width
            kw_length + 1.0,  # axial length (slightly longer for clean cut)
            align=(Align.MIN, Align.CENTER, Align.CENTER)
        )
        # Position starting from center (X=0), extending in +X direction
        # No translation needed - MIN alignment puts it at origin
    else:
        # Hub keyway (wheel): cut into the hub material around the bore
        # The slot extends from inside the bore outward through the hub material
        # DIN 6885 t2 is measured from the bore surface outward
        #
        # To avoid a facet covering the bore, extend the box inward past the
        # bore surface so it fully intersects with the cylindrical bore
        keyway_box = Box(
            bore_radius + depth,  # from center to (bore_radius + depth)
            width,  # tangential width
            kw_length + 1.0,  # axial length (slightly longer for clean cut)
            align=(Align.MIN, Align.CENTER, Align.CENTER)
        )
        # Position starting from center (X=0), extending in +X direction
        # No translation needed - MIN alignment puts it at origin

    # Rotate to correct axis if needed
    if axis == Axis.X:
        keyway_box = keyway_box.rotate(Axis.Y, 90)
    elif axis == Axis.Y:
        keyway_box = keyway_box.rotate(Axis.X, 90)

    # Subtract from part
    result = part - keyway_box

    return result


def create_set_screw(
    part: Part,
    bore: BoreFeature,
    set_screw: SetScrewFeature,
    part_length: float,
    axis: Axis = Axis.Z
) -> Part:
    """
    Create set screw holes in a part (requires bore to already exist or be specified).

    Set screws are drilled radially through the bore wall. Multiple set screws
    are evenly spaced around the circumference.

    Args:
        part: The part to add set screw holes to
        bore: Bore specification (set screws go through bore wall)
        set_screw: Set screw specification
        part_length: Length of the part along axis
        axis: Axis along which part is oriented (default: Z)

    Returns:
        Part with set screw holes cut
    """
    bore_radius = bore.diameter / 2
    screw_size, screw_diameter = set_screw.get_screw_specs(bore.diameter)

    # Set screw holes are drilled radially (perpendicular to axis)
    # They should extend from outside the part through the bore wall
    # Use a generous length to ensure they fully penetrate
    screw_hole_length = bore_radius + 10.0  # Extend 10mm beyond center

    # Calculate angular positions for multiple set screws
    # Evenly distributed around circumference
    if set_screw.count == 1:
        angles = [set_screw.angular_offset]
    else:
        # Multiple screws: distribute evenly (e.g., 2 screws = 180° apart)
        angle_step = 360.0 / set_screw.count
        angles = [set_screw.angular_offset + i * angle_step for i in range(set_screw.count)]

    result = part

    for angle in angles:
        # Create cylindrical hole for set screw
        # The hole is positioned at the bore surface and drilled radially inward
        screw_hole = Cylinder(
            radius=screw_diameter / 2,
            height=screw_hole_length,
            align=(Align.MIN, Align.CENTER, Align.CENTER)
        )

        # Position and orient the hole based on axis
        if axis == Axis.Z:
            # Part is along Z axis, set screw holes are in XY plane
            # Rotate hole to be radial at the specified angle
            screw_hole = screw_hole.rotate(Axis.Z, angle)
        elif axis == Axis.X:
            # Part is along X axis, set screw holes are in YZ plane
            screw_hole = screw_hole.rotate(Axis.Y, 90)  # Orient along X
            screw_hole = screw_hole.rotate(Axis.X, angle)
        elif axis == Axis.Y:
            # Part is along Y axis, set screw holes are in XZ plane
            screw_hole = screw_hole.rotate(Axis.X, -90)  # Orient along Y
            screw_hole = screw_hole.rotate(Axis.Y, angle)

        # Subtract from part
        result = result - screw_hole

    return result


def create_ddcut(
    part: Part,
    bore: BoreFeature,
    ddcut: DDCutFeature,
    part_length: float,
    axis: Axis = Axis.Z
) -> Part:
    """
    Create double-D cut flats in a bore for anti-rotation (requires bore to already exist).

    Creates two parallel flat cuts on opposite sides of the bore, forming
    a D-shape when viewed from two perpendicular directions. This provides
    excellent anti-rotation for small shafts where keyways are impractical.

    NOTE: This fills in portions of the circular bore to create flats, making
    the effective bore diameter smaller in one direction.

    Args:
        part: The part to modify (must already have bore created)
        bore: Bore feature specification (for diameter)
        ddcut: DD-cut feature specification (depth validation occurs in ddcut.get_depth())
        part_length: Length of part along axis
        axis: Axis of bore (default: Z)

    Returns:
        Modified part with DD-cut flats

    Raises:
        ValueError: If DD-cut depth is invalid (raised by ddcut.get_depth())
    """
    bore_radius = bore.diameter / 2
    flat_depth = ddcut.get_depth(bore.diameter)

    # The flat position is at distance (bore_radius - flat_depth) from center
    flat_position = bore_radius - flat_depth

    # Create boxes to FILL IN the bore region beyond the flats
    # This adds material back into the circular bore to create the flats
    # Box extends from flat_position outward to bore_radius (exactly)
    box_thickness = flat_depth  # Thickness of material to add back (no excess)

    # Calculate chord width at the flat position for precise box sizing
    # For a circle, chord_half_width = sqrt(R^2 - d^2) where d is distance from center
    under_sqrt = bore_radius**2 - flat_position**2
    if under_sqrt < 0:
        raise ValueError(
            f"DD-cut flat_depth ({flat_depth}mm) exceeds bore_radius ({bore_radius}mm). "
            f"Maximum flat_depth is {bore_radius * 0.85:.2f}mm for bore diameter {bore_diameter}mm."
        )
    chord_half_width = math.sqrt(under_sqrt)
    box_width = 2 * chord_half_width  # Exact width of chord at flat position

    box_height = part_length  # Exact length along bore axis (no extension)

    # Create filling boxes based on axis orientation
    if axis == Axis.Z:
        # Bore along Z axis, flats perpendicular to X axis
        # Fill from flat_position to bore_radius on +X side
        fill1 = Box(box_thickness, box_width, box_height,
                   align=(Align.MIN, Align.CENTER, Align.CENTER))
        fill1 = Pos(flat_position, 0, 0) * fill1

        # Fill from -flat_position to -bore_radius on -X side
        fill2 = Box(box_thickness, box_width, box_height,
                   align=(Align.MAX, Align.CENTER, Align.CENTER))
        fill2 = Pos(-flat_position, 0, 0) * fill2

    elif axis == Axis.X:
        # Bore along X axis, flats perpendicular to Y axis
        fill1 = Box(box_height, box_thickness, box_width,
                   align=(Align.CENTER, Align.MIN, Align.CENTER))
        fill1 = Pos(0, flat_position, 0) * fill1

        fill2 = Box(box_height, box_thickness, box_width,
                   align=(Align.CENTER, Align.MAX, Align.CENTER))
        fill2 = Pos(0, -flat_position, 0) * fill2

    elif axis == Axis.Y:
        # Bore along Y axis, flats perpendicular to Z axis
        fill1 = Box(box_width, box_height, box_thickness,
                   align=(Align.CENTER, Align.CENTER, Align.MIN))
        fill1 = Pos(0, 0, flat_position) * fill1

        fill2 = Box(box_width, box_height, box_thickness,
                   align=(Align.CENTER, Align.CENTER, Align.MAX))
        fill2 = Pos(0, 0, -flat_position) * fill2

    # Create a cylinder at bore radius to constrain radial extent of fills
    # This prevents fills from extending beyond the nominal bore boundary
    # Height is slightly longer (+1mm) than part to ensure clean intersection at ends
    if axis == Axis.Z:
        bore_boundary = Cylinder(
            radius=bore_radius,
            height=part_length + 1.0,  # +1mm ensures clean intersection at part ends
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
    elif axis == Axis.X:
        bore_boundary = Cylinder(
            radius=bore_radius,
            height=part_length + 1.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
        bore_boundary = bore_boundary.rotate(Axis.Y, 90)
    elif axis == Axis.Y:
        bore_boundary = Cylinder(
            radius=bore_radius,
            height=part_length + 1.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
        bore_boundary = bore_boundary.rotate(Axis.X, 90)

    # Apply angular offset to fill boxes if specified
    if ddcut.angular_offset != 0:
        fill1 = fill1.rotate(axis, ddcut.angular_offset)
        fill2 = fill2.rotate(axis, ddcut.angular_offset)

    # Constrain fills using two operations:
    # 1. Intersect with bore_boundary to limit radial extent to bore radius
    # 2. Subtract solid part to only keep portion in the bore hole
    # This ensures fills only occupy bore space and don't extend beyond part surface
    fill1 = (fill1 & bore_boundary) - part
    fill2 = (fill2 & bore_boundary) - part

    # UNION the constrained fills back into the part to create flats in the bore
    result = part + fill1 + fill2

    return result


def create_hub(
    wheel: Part,
    hub: HubFeature,
    wheel_face_width: float,
    wheel_root_diameter: float,
    bore_diameter: Optional[float] = None,
    axis: Axis = Axis.Z
) -> Part:
    """
    Create hub extension on a wheel (additive feature).

    Hubs extend from the wheel face to provide mounting surface.
    This is an additive operation - it adds material to the wheel.

    Args:
        wheel: The wheel part to add hub to
        hub: Hub specification
        wheel_face_width: Face width of the wheel
        wheel_root_diameter: Root diameter of wheel (to size hub properly)
        bore_diameter: Bore diameter if present (hub must fit around it)
        axis: Axis along which wheel is oriented (default: Z)

    Returns:
        Wheel with hub added

    Raises:
        ValueError: If hub parameters are invalid for wheel size
    """
    if hub.hub_type == "flush":
        # Flush hub - no extension, just return wheel as-is
        return wheel

    # Hub inner diameter is slightly larger than bore (if present) or very small
    if bore_diameter is not None:
        hub_inner_diameter = bore_diameter
    else:
        hub_inner_diameter = 0.0  # Solid hub if no bore

    # Hub outer diameter - use wheel root diameter as base
    # Make hub slightly smaller than root to avoid interfering with teeth
    hub_outer_diameter = wheel_root_diameter * 0.8

    # Extended or flanged hub
    if hub.hub_type in ["extended", "flanged"]:
        # Create hub cylinder extending from wheel face
        hub_cylinder = Cylinder(
            radius=hub_outer_diameter / 2,
            height=hub.length,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        )

        # Position hub to extend from one face of wheel
        # Wheel is centered, so move hub to start at +face_width/2
        if axis == Axis.Z:
            hub_cylinder = hub_cylinder.move(Location((0, 0, wheel_face_width / 2)))
        elif axis == Axis.X:
            hub_cylinder = hub_cylinder.rotate(Axis.Y, 90)
            hub_cylinder = hub_cylinder.move(Location((wheel_face_width / 2, 0, 0)))
        elif axis == Axis.Y:
            hub_cylinder = hub_cylinder.rotate(Axis.X, 90)
            hub_cylinder = hub_cylinder.move(Location((0, wheel_face_width / 2, 0)))

        # Remove bore from hub if needed
        if bore_diameter is not None and bore_diameter > 0:
            bore_length = hub.length + 1.0  # Slightly longer
            hub_bore = Cylinder(
                radius=bore_diameter / 2,
                height=bore_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
            if axis == Axis.Z:
                hub_bore = hub_bore.move(Location((0, 0, wheel_face_width / 2)))
            elif axis == Axis.X:
                hub_bore = hub_bore.rotate(Axis.Y, 90)
                hub_bore = hub_bore.move(Location((wheel_face_width / 2, 0, 0)))
            elif axis == Axis.Y:
                hub_bore = hub_bore.rotate(Axis.X, 90)
                hub_bore = hub_bore.move(Location((0, wheel_face_width / 2, 0)))

            hub_cylinder = hub_cylinder - hub_bore

        result = wheel + hub_cylinder

    # Flanged hub - add flange at end of hub extension
    if hub.hub_type == "flanged":
        # Determine flange diameter
        if hub.flange_diameter is None:
            # Auto-size: 1.5x hub outer diameter, but at least 1.3x
            hub.flange_diameter = max(
                hub_outer_diameter * 1.5,
                hub_outer_diameter + 20.0  # At least 20mm larger
            )

        # Validate flange diameter
        if hub.flange_diameter <= hub_outer_diameter:
            raise ValueError(
                f"Flange diameter ({hub.flange_diameter}mm) must be larger than "
                f"hub diameter ({hub_outer_diameter}mm)"
            )

        # Create flange disk
        flange = Cylinder(
            radius=hub.flange_diameter / 2,
            height=hub.flange_thickness,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        )

        # Position flange at end of hub
        flange_position = wheel_face_width / 2 + hub.length
        if axis == Axis.Z:
            flange = flange.move(Location((0, 0, flange_position)))
        elif axis == Axis.X:
            flange = flange.rotate(Axis.Y, 90)
            flange = flange.move(Location((flange_position, 0, 0)))
        elif axis == Axis.Y:
            flange = flange.rotate(Axis.X, 90)
            flange = flange.move(Location((0, flange_position, 0)))

        # Remove center bore from flange if present
        if bore_diameter is not None and bore_diameter > 0:
            flange_bore = Cylinder(
                radius=bore_diameter / 2,
                height=hub.flange_thickness + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
            if axis == Axis.Z:
                flange_bore = flange_bore.move(Location((0, 0, flange_position)))
            elif axis == Axis.X:
                flange_bore = flange_bore.rotate(Axis.Y, 90)
                flange_bore = flange_bore.move(Location((flange_position, 0, 0)))
            elif axis == Axis.Y:
                flange_bore = flange_bore.rotate(Axis.X, 90)
                flange_bore = flange_bore.move(Location((0, flange_position, 0)))

            flange = flange - flange_bore

        # Add bolt holes if requested
        if hub.bolt_holes > 0:
            # Determine bolt diameter
            if hub.bolt_diameter is None:
                # Auto-size based on flange
                # Typical: M4 for small flanges, M5 for medium, M6 for large
                if hub.flange_diameter < 50:
                    hub.bolt_diameter = 4.5  # M4 clearance hole
                elif hub.flange_diameter < 80:
                    hub.bolt_diameter = 5.5  # M5 clearance hole
                else:
                    hub.bolt_diameter = 6.5  # M6 clearance hole

            # Bolt circle diameter - midway between hub OD and flange OD
            bolt_circle_radius = (hub_outer_diameter / 2 + hub.flange_diameter / 2) / 2

            # Create bolt holes evenly distributed
            angle_step = 360.0 / hub.bolt_holes
            for i in range(hub.bolt_holes):
                angle = i * angle_step
                angle_rad = math.radians(angle)

                # Calculate bolt hole position
                bolt_x = bolt_circle_radius * math.cos(angle_rad)
                bolt_y = bolt_circle_radius * math.sin(angle_rad)

                # Create bolt hole
                bolt_hole = Cylinder(
                    radius=hub.bolt_diameter / 2,
                    height=hub.flange_thickness + 1.0,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                )

                # Position and orient based on axis
                if axis == Axis.Z:
                    bolt_hole = bolt_hole.move(Location((bolt_x, bolt_y, flange_position)))
                elif axis == Axis.X:
                    bolt_hole = bolt_hole.rotate(Axis.Y, 90)
                    bolt_hole = bolt_hole.move(Location((flange_position, bolt_y, bolt_x)))
                elif axis == Axis.Y:
                    bolt_hole = bolt_hole.rotate(Axis.X, 90)
                    bolt_hole = bolt_hole.move(Location((bolt_x, flange_position, bolt_y)))

                flange = flange - bolt_hole

        result = result + flange

    return result


def add_bore_and_keyway(
    part: Part,
    part_length: float,
    bore: Optional[BoreFeature] = None,
    keyway: Optional[KeywayFeature] = None,
    ddcut: Optional[DDCutFeature] = None,
    set_screw: Optional[SetScrewFeature] = None,
    axis: Axis = Axis.Z
) -> Part:
    """
    Add bore, keyway/DD-cut, and set screw holes to a part.

    Convenience function that applies features in order:
    bore → keyway/DD-cut → set screws.

    Note: keyway and ddcut are mutually exclusive (use one or the other).

    Args:
        part: The part to modify
        part_length: Length of the part along axis
        bore: Bore specification (required if keyway, ddcut, or set_screw specified)
        keyway: Keyway specification (optional, mutually exclusive with ddcut)
        ddcut: Double-D cut specification (optional, mutually exclusive with keyway)
        set_screw: Set screw specification (optional)
        axis: Axis for bore and features (default: Z)

    Returns:
        Modified part with requested features

    Raises:
        ValueError: If keyway/ddcut/set_screw specified without bore,
                   or if both keyway and ddcut specified
    """
    if keyway is not None and bore is None:
        raise ValueError("Keyway requires a bore to be specified")

    if ddcut is not None and bore is None:
        raise ValueError("DD-cut requires a bore to be specified")

    if keyway is not None and ddcut is not None:
        raise ValueError("Cannot specify both keyway and DD-cut - choose one")

    if set_screw is not None and bore is None:
        raise ValueError("Set screw requires a bore to be specified")

    result = part

    if bore is not None:
        result = create_bore(result, bore, part_length, axis)

    if keyway is not None:
        result = create_keyway(result, bore, keyway, part_length, axis)

    if ddcut is not None:
        result = create_ddcut(result, bore, ddcut, part_length, axis)

    if set_screw is not None:
        result = create_set_screw(result, bore, set_screw, part_length, axis)

    # Ensure we return a single Part/Solid, not a ShapeList
    # Boolean operations can sometimes split geometry into multiple pieces
    if hasattr(result, 'solids'):
        solids = list(result.solids())
        if len(solids) == 1:
            result = solids[0]
        elif len(solids) > 1:
            # Return the largest solid (the main part)
            result = max(solids, key=lambda s: s.volume)

    return result
