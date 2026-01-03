"""QFP/LQFP/TQFP footprint generator."""

import math

from kiforge.core.footprint.generator import (
    Arc,
    Circle,
    FootprintGenerator,
    Line,
    Pad,
)
from kiforge.core.models.enums import PadShape
from kiforge.core.models.footprint import FootprintParams


class QFPFootprintGenerator(FootprintGenerator):
    """Generator for QFP family footprints (QFP, LQFP, TQFP, VQFP).

    QFP packages have gull-wing leads on all four sides with pin 1
    at the top-left corner. Pins are numbered counter-clockwise.
    """

    def calculate_pads(self) -> None:
        """Calculate pad positions for all four sides.

        Pin numbering for QFP (counter-clockwise from pin 1):
        - Side 1 (left): pins 1 to N/4, going downward
        - Side 2 (bottom): pins N/4+1 to N/2, going right
        - Side 3 (right): pins N/2+1 to 3N/4, going upward
        - Side 4 (top): pins 3N/4+1 to N, going left
        """
        pkg = self.params.package
        pad_size = self.params.pad_size

        # Number of pins per side
        pins_per_side = pkg.pins_per_side
        if pins_per_side is None:
            raise ValueError("Package must have pins_per_side for QFP")

        pitch = pkg.pitch
        total_pins = pins_per_side * 4

        # Calculate the array span (distance from first to last pin center on each side)
        array_span = (pins_per_side - 1) * pitch

        # Pad center offset from origin (X for left/right, Y for top/bottom)
        pad_x = self.params.pad_center_x
        pad_y = self.params.pad_center_y

        # Starting Y position for side 1 (left) - top of the array
        start_y = -array_span / 2

        pin_number = 1

        # Side 1 - Left side (pins going downward)
        for i in range(pins_per_side):
            y = start_y + i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=-pad_x,
                    y=y,
                    width=pad_size.width,
                    height=pad_size.height,
                    rotation=0,  # Horizontal pad
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Starting X position for side 2 (bottom) - left of the array
        start_x = -array_span / 2

        # Side 2 - Bottom side (pins going right)
        for i in range(pins_per_side):
            x = start_x + i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=x,
                    y=pad_y,
                    width=pad_size.height,  # Swap for vertical orientation
                    height=pad_size.width,
                    rotation=0,  # Rotated pad (swap width/height)
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Starting Y position for side 3 (right) - bottom of the array
        start_y = array_span / 2

        # Side 3 - Right side (pins going upward)
        for i in range(pins_per_side):
            y = start_y - i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=pad_x,
                    y=y,
                    width=pad_size.width,
                    height=pad_size.height,
                    rotation=0,  # Horizontal pad
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Starting X position for side 4 (top) - right of the array
        start_x = array_span / 2

        # Side 4 - Top side (pins going left)
        for i in range(pins_per_side):
            x = start_x - i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=x,
                    y=-pad_y,
                    width=pad_size.height,  # Swap for vertical orientation
                    height=pad_size.width,
                    rotation=0,  # Rotated pad (swap width/height)
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

    def calculate_silkscreen(self) -> None:
        """Calculate silkscreen with cutouts for pads and pin 1 marker."""
        pkg = self.params.package
        pad_size = self.params.pad_size
        margin = self.params.silkscreen_margin
        width = self.params.silkscreen_line_width

        # Body outline position
        body_half_w = pkg.body_width / 2
        body_half_h = pkg.body_length / 2

        # Pad extents - where silkscreen must not overlap
        pad_x = self.params.pad_center_x
        pad_y = self.params.pad_center_y
        pad_edge_x = pad_x - pad_size.width / 2 - margin
        pad_edge_y = pad_y - pad_size.height / 2 - margin

        # Pin array span
        pins_per_side = pkg.pins_per_side or 1
        pitch = pkg.pitch
        array_half = (pins_per_side - 1) * pitch / 2 + pad_size.height / 2 + margin

        # Draw silkscreen lines around the body, avoiding pad areas

        # Top-left corner to top-right corner (with gaps for pads)
        # Left segment
        if body_half_w > pad_edge_x:
            self.lines.append(Line(-body_half_w, -body_half_h, -pad_edge_x, -body_half_h, "F.SilkS", width))
        # Right segment
        if body_half_w > pad_edge_x:
            self.lines.append(Line(pad_edge_x, -body_half_h, body_half_w, -body_half_h, "F.SilkS", width))

        # Bottom edge
        if body_half_w > pad_edge_x:
            self.lines.append(Line(-body_half_w, body_half_h, -pad_edge_x, body_half_h, "F.SilkS", width))
        if body_half_w > pad_edge_x:
            self.lines.append(Line(pad_edge_x, body_half_h, body_half_w, body_half_h, "F.SilkS", width))

        # Left edge (with gaps for pads)
        if body_half_h > pad_edge_y:
            self.lines.append(Line(-body_half_w, -body_half_h, -body_half_w, -pad_edge_y, "F.SilkS", width))
        if body_half_h > pad_edge_y:
            self.lines.append(Line(-body_half_w, pad_edge_y, -body_half_w, body_half_h, "F.SilkS", width))

        # Right edge
        if body_half_h > pad_edge_y:
            self.lines.append(Line(body_half_w, -body_half_h, body_half_w, -pad_edge_y, "F.SilkS", width))
        if body_half_h > pad_edge_y:
            self.lines.append(Line(body_half_w, pad_edge_y, body_half_w, body_half_h, "F.SilkS", width))

        # Pin 1 marker - dot near top-left corner
        pin1_marker_x = -pad_x - pad_size.width / 2 - 0.5
        pin1_marker_y = -array_half
        marker_radius = 0.2

        self.circles.append(Circle(pin1_marker_x, pin1_marker_y, marker_radius, "F.SilkS", width, fill=True))


def create_qfp_footprint(
    pins: int,
    pitch: float,
    body_width: float,
    body_length: float,
    lead_span: float,
    body_height: float = 1.4,
    lead_width: float | None = None,
    variant: str = "LQFP",
) -> str:
    """Create a QFP footprint with the given parameters.

    Args:
        pins: Total pin count (must be divisible by 4)
        pitch: Pin pitch in mm
        body_width: Package body width in mm
        body_length: Package body length in mm
        lead_span: Lead span (tip to tip) in mm
        body_height: Package height (determines variant)
        lead_width: Lead width (defaults to 0.6 * pitch)
        variant: QFP variant name

    Returns:
        KiCad footprint file content
    """
    from kiforge.core.models.enums import PackageType
    from kiforge.core.models.footprint import PadDimensions
    from kiforge.core.models.package import PackageInfo

    if pins % 4 != 0:
        raise ValueError("QFP pin count must be divisible by 4")

    if lead_width is None:
        lead_width = pitch * 0.6

    # Determine package type from variant
    variant_upper = variant.upper()
    if variant_upper in ("LQFP", "TQFP", "VQFP", "QFP"):
        pkg_type = PackageType[variant_upper]
    else:
        pkg_type = PackageType.LQFP

    # Create package info
    package = PackageInfo(
        package_type=pkg_type,
        package_name=f"{variant}-{pins}",
        pin_count=pins,
        pitch=pitch,
        body_width=body_width,
        body_length=body_length,
        body_height=body_height,
        lead_width=lead_width,
        lead_span=lead_span,
    )

    # Calculate pad dimensions
    # Pad length extends from body edge to slightly beyond lead tip
    pad_length = (lead_span - body_width) / 2 + 0.5  # 0.5mm extension
    pad_width = pitch * 0.55  # Standard pad width ratio

    pad_size = PadDimensions(
        width=pad_length,
        height=pad_width,
        corner_ratio=0.25,
    )

    # Pad center position
    pad_center = (body_width / 2 + pad_length / 2)

    # Create footprint name
    fp_name = f"{variant}-{pins}_{body_width}x{body_length}mm_P{pitch}mm"

    # Create params
    params = FootprintParams(
        footprint_name=fp_name,
        description=f"{variant}, {pins} Pin, {body_width}x{body_length}mm body, {pitch}mm pitch",
        tags=[variant, "QFP", f"{pins}-pin"],
        package=package,
        pad_size=pad_size,
        pad_center_x=pad_center,
        pad_center_y=pad_center,
    )

    # Generate
    generator = QFPFootprintGenerator(params)
    return generator.generate()
