"""QFN/DFN footprint generator."""

from kiforge.core.footprint.generator import (
    Circle,
    FootprintGenerator,
    Line,
    Pad,
)
from kiforge.core.models.enums import PadShape, PadType
from kiforge.core.models.footprint import FootprintParams, PadDimensions
from kiforge.core.models.package import PackageInfo, ThermalPad


class QFNFootprintGenerator(FootprintGenerator):
    """Generator for QFN/DFN family footprints.

    QFN (Quad Flat No-lead) packages have terminals on the bottom edge
    of the package with no leads extending beyond the body. They typically
    have an exposed thermal pad in the center.

    Pin numbering (counter-clockwise from pin 1):
    - QFN: pins on all 4 sides
    - DFN: pins on 2 sides (left and right)
    """

    def calculate_pads(self) -> None:
        """Calculate pad positions for QFN/DFN package."""
        pkg = self.params.package
        pad_size = self.params.pad_size

        # Determine if this is a quad (4-sided) or dual (2-sided) package
        is_dual = pkg.is_dual

        if is_dual:
            self._calculate_dual_pads()
        else:
            self._calculate_quad_pads()

    def _calculate_quad_pads(self) -> None:
        """Calculate pad positions for 4-sided QFN package."""
        pkg = self.params.package
        pad_size = self.params.pad_size

        # Get pin count (excluding thermal pad)
        total_pins = pkg.pin_count
        if pkg.has_thermal_pad:
            total_pins -= 1

        pins_per_side = total_pins // 4
        pitch = pkg.pitch

        # Calculate array span
        array_span = (pins_per_side - 1) * pitch

        # Pad center position - at the edge of the package body
        # For QFN, pads are at body_width/2 (package edge)
        pad_x = self.params.pad_center_x
        pad_y = self.params.pad_center_y

        # Starting position for first pin on each side
        start_pos = -array_span / 2

        pin_number = 1

        # Side 1 - Left side (pins going downward)
        for i in range(pins_per_side):
            y = start_pos + i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=-pad_x,
                    y=y,
                    width=pad_size.width,
                    height=pad_size.height,
                    rotation=0,
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Side 2 - Bottom side (pins going right)
        for i in range(pins_per_side):
            x = start_pos + i * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=x,
                    y=pad_y,
                    width=pad_size.height,  # Swap for vertical orientation
                    height=pad_size.width,
                    rotation=0,
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Side 3 - Right side (pins going upward)
        for i in range(pins_per_side):
            y = start_pos + (pins_per_side - 1 - i) * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=pad_x,
                    y=y,
                    width=pad_size.width,
                    height=pad_size.height,
                    rotation=0,
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Side 4 - Top side (pins going left)
        for i in range(pins_per_side):
            x = start_pos + (pins_per_side - 1 - i) * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=x,
                    y=-pad_y,
                    width=pad_size.height,  # Swap for vertical orientation
                    height=pad_size.width,
                    rotation=0,
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

    def _calculate_dual_pads(self) -> None:
        """Calculate pad positions for 2-sided DFN package."""
        pkg = self.params.package
        pad_size = self.params.pad_size

        # Get pin count (excluding thermal pad)
        total_pins = pkg.pin_count
        if pkg.has_thermal_pad:
            total_pins -= 1

        pins_per_side = total_pins // 2
        pitch = pkg.pitch

        # Calculate array span
        array_span = (pins_per_side - 1) * pitch

        # Pad center position
        pad_x = self.params.pad_center_x

        # Starting position
        start_y = -array_span / 2

        pin_number = 1

        # Left side (pins going downward)
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
                    rotation=0,
                    roundrect_ratio=pad_size.corner_ratio,
                )
            )
            pin_number += 1

        # Right side (pins going upward)
        for i in range(pins_per_side):
            y = start_y + (pins_per_side - 1 - i) * pitch
            self.pads.append(
                Pad(
                    number=str(pin_number),
                    pad_type=self.params.pad_type,
                    shape=pad_size.shape,
                    x=pad_x,
                    y=y,
                    width=pad_size.width,
                    height=pad_size.height,
                    rotation=0,
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

        # Body outline
        body_half_w = pkg.body_width / 2
        body_half_h = pkg.body_length / 2

        # Pad extents - where silkscreen must not overlap
        pad_x = self.params.pad_center_x
        pad_y = self.params.pad_center_y

        # For QFN, pads extend into the body, so we draw outside the pads
        # Calculate where pads end (inner edge of pads)
        pad_inner_x = pad_x - pad_size.width / 2 - margin
        pad_inner_y = pad_y - pad_size.width / 2 - margin  # Using width because pads are rotated

        # Pin array span
        pins_per_side = pkg.pins_per_side or (pkg.pin_count // 4)
        pitch = pkg.pitch
        array_half = (pins_per_side - 1) * pitch / 2 + pad_size.height / 2 + margin

        # Draw corner marks only (to avoid overlapping with pads)
        corner_len = min(1.0, body_half_w * 0.3)

        # Top-left corner (with pin 1 marker)
        self.lines.append(Line(-body_half_w, -body_half_h + corner_len, -body_half_w, -body_half_h, "F.SilkS", width))
        self.lines.append(Line(-body_half_w, -body_half_h, -body_half_w + corner_len, -body_half_h, "F.SilkS", width))

        # Top-right corner
        self.lines.append(Line(body_half_w - corner_len, -body_half_h, body_half_w, -body_half_h, "F.SilkS", width))
        self.lines.append(Line(body_half_w, -body_half_h, body_half_w, -body_half_h + corner_len, "F.SilkS", width))

        # Bottom-right corner
        self.lines.append(Line(body_half_w, body_half_h - corner_len, body_half_w, body_half_h, "F.SilkS", width))
        self.lines.append(Line(body_half_w, body_half_h, body_half_w - corner_len, body_half_h, "F.SilkS", width))

        # Bottom-left corner
        self.lines.append(Line(-body_half_w + corner_len, body_half_h, -body_half_w, body_half_h, "F.SilkS", width))
        self.lines.append(Line(-body_half_w, body_half_h, -body_half_w, body_half_h - corner_len, "F.SilkS", width))

        # Pin 1 marker - dot near top-left corner
        marker_x = -body_half_w - 0.5
        marker_y = -array_half
        marker_radius = 0.2
        self.circles.append(Circle(marker_x, marker_y, marker_radius, "F.SilkS", width, fill=True))


def create_qfn_footprint(
    pins: int,
    pitch: float,
    body_width: float,
    body_length: float | None = None,
    body_height: float = 0.9,
    terminal_length: float | None = None,
    terminal_width: float | None = None,
    thermal_pad_size: float | None = None,
    variant: str = "QFN",
) -> str:
    """Create a QFN/DFN footprint with the given parameters.

    Args:
        pins: Total pin count (must be divisible by 4 for QFN, 2 for DFN)
        pitch: Pin pitch in mm
        body_width: Package body width in mm
        body_length: Package body length in mm (defaults to body_width)
        body_height: Package height in mm
        terminal_length: Terminal length in mm (defaults to 0.4)
        terminal_width: Terminal width in mm (defaults to pitch * 0.5)
        thermal_pad_size: Thermal pad size in mm (defaults to body_width * 0.6)
        variant: QFN variant name (QFN, DFN, VQFN, WQFN)

    Returns:
        KiCad footprint file content
    """
    from kiforge.core.models.enums import PackageType

    if body_length is None:
        body_length = body_width

    if terminal_length is None:
        terminal_length = 0.4

    if terminal_width is None:
        terminal_width = pitch * 0.5

    if thermal_pad_size is None:
        thermal_pad_size = min(body_width, body_length) * 0.6

    # Validate pin count
    variant_upper = variant.upper()
    if variant_upper == "DFN":
        if pins % 2 != 0:
            raise ValueError("DFN pin count must be divisible by 2")
        pkg_type = PackageType.DFN
    else:
        if pins % 4 != 0:
            raise ValueError("QFN pin count must be divisible by 4")
        pkg_type = PackageType.QFN
        if variant_upper == "VQFN":
            pkg_type = PackageType.VQFN
        elif variant_upper == "WQFN":
            pkg_type = PackageType.WQFN

    # Create thermal pad
    thermal_pad = ThermalPad(
        width=thermal_pad_size,
        height=thermal_pad_size,
        via_count_x=3,
        via_count_y=3,
        via_drill=0.3,
        via_pad_diameter=0.5,
        pin_number="EP",
    )

    # Create package info
    package = PackageInfo(
        package_type=pkg_type,
        package_name=f"{variant_upper}-{pins}",
        pin_count=pins + 1,  # +1 for thermal pad
        pitch=pitch,
        body_width=body_width,
        body_length=body_length,
        body_height=body_height,
        thermal_pad=thermal_pad,
    )

    # Calculate pad dimensions
    # Pad extends from body edge inward by terminal_length
    # Plus some extension outward for soldering (~0.2mm)
    pad_length = terminal_length + 0.3
    pad_width = terminal_width

    pad_size = PadDimensions(
        width=pad_length,
        height=pad_width,
        shape=PadShape.ROUNDRECT,
        corner_ratio=0.25,
    )

    # Pad center position - at body edge minus half pad length
    pad_center = body_width / 2 - terminal_length / 2 + 0.15

    # Create footprint name
    fp_name = f"{variant_upper}-{pins}-1EP_{body_width}x{body_length}mm_P{pitch}mm_EP{thermal_pad_size}x{thermal_pad_size}mm"

    # Create params
    params = FootprintParams(
        footprint_name=fp_name,
        description=f"{variant_upper}, {pins} Pin, {body_width}x{body_length}mm body, {pitch}mm pitch, {thermal_pad_size}mm exposed pad",
        tags=[variant_upper, "QFN", "DFN", f"{pins}-pin", "EP"],
        package=package,
        pad_size=pad_size,
        pad_center_x=pad_center,
        pad_center_y=pad_center,
    )

    # Generate
    generator = QFNFootprintGenerator(params)
    return generator.generate()
