"""Base footprint generator with S-expression output."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from kiforge.core.models.enums import PadShape, PadType
from kiforge.core.models.footprint import FootprintParams, PadDimensions
from kiforge.core.models.package import ThermalPad


# KiCad 8 format version (YYYYMMDD)
KICAD_VERSION = 20241229


@dataclass
class Pad:
    """Represents a footprint pad."""

    number: str
    pad_type: PadType
    shape: PadShape
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    layers: list[str] = field(default_factory=lambda: ["F.Cu", "F.Paste", "F.Mask"])
    roundrect_ratio: float = 0.25
    drill: float | None = None
    drill_oval: tuple[float, float] | None = None
    property_heatsink: bool = False


@dataclass
class Line:
    """Represents a line on the footprint."""

    x1: float
    y1: float
    x2: float
    y2: float
    layer: str
    width: float


@dataclass
class Circle:
    """Represents a circle on the footprint."""

    cx: float
    cy: float
    radius: float
    layer: str
    width: float
    fill: bool = False


@dataclass
class Arc:
    """Represents an arc on the footprint."""

    start_x: float
    start_y: float
    mid_x: float
    mid_y: float
    end_x: float
    end_y: float
    layer: str
    width: float


@dataclass
class Text:
    """Represents text on the footprint."""

    text_type: str  # "reference", "value", "user"
    text: str
    x: float
    y: float
    layer: str
    font_size: float = 1.0
    font_thickness: float = 0.15
    hide: bool = False


class FootprintGenerator(ABC):
    """Base class for footprint generators.

    Provides common functionality for generating KiCad footprint files
    in S-expression format.
    """

    def __init__(self, params: FootprintParams):
        """Initialize the generator.

        Args:
            params: Footprint parameters
        """
        self.params = params
        self.pads: list[Pad] = []
        self.lines: list[Line] = []
        self.circles: list[Circle] = []
        self.arcs: list[Arc] = []
        self.texts: list[Text] = []

    @abstractmethod
    def calculate_pads(self) -> None:
        """Calculate pad positions. Must be implemented by subclasses."""
        pass

    def calculate_silkscreen(self) -> None:
        """Calculate silkscreen graphics."""
        # Default implementation draws a rectangle around the package body
        pkg = self.params.package
        margin = self.params.silkscreen_margin
        width = self.params.silkscreen_line_width

        # Offset from pad centers
        half_w = pkg.body_width / 2 + margin
        half_h = pkg.body_length / 2 + margin

        # Draw body outline on silkscreen (simple rectangle)
        # Top line
        self.lines.append(Line(-half_w, -half_h, half_w, -half_h, "F.SilkS", width))
        # Bottom line
        self.lines.append(Line(-half_w, half_h, half_w, half_h, "F.SilkS", width))
        # Left line
        self.lines.append(Line(-half_w, -half_h, -half_w, half_h, "F.SilkS", width))
        # Right line
        self.lines.append(Line(half_w, -half_h, half_w, half_h, "F.SilkS", width))

    def calculate_courtyard(self) -> None:
        """Calculate courtyard boundary."""
        # Find the extents of all pads
        if not self.pads:
            return

        min_x = min(p.x - p.width / 2 for p in self.pads)
        max_x = max(p.x + p.width / 2 for p in self.pads)
        min_y = min(p.y - p.height / 2 for p in self.pads)
        max_y = max(p.y + p.height / 2 for p in self.pads)

        margin = self.params.courtyard_margin
        width = self.params.courtyard_line_width

        # Round to 0.01mm grid
        min_x = round(min_x - margin, 2)
        max_x = round(max_x + margin, 2)
        min_y = round(min_y - margin, 2)
        max_y = round(max_y + margin, 2)

        # Draw courtyard rectangle
        self.lines.append(Line(min_x, min_y, max_x, min_y, "F.CrtYd", width))
        self.lines.append(Line(max_x, min_y, max_x, max_y, "F.CrtYd", width))
        self.lines.append(Line(max_x, max_y, min_x, max_y, "F.CrtYd", width))
        self.lines.append(Line(min_x, max_y, min_x, min_y, "F.CrtYd", width))

    def calculate_fab_layer(self) -> None:
        """Calculate fabrication layer graphics (actual component outline)."""
        pkg = self.params.package
        width = self.params.fab_line_width

        half_w = pkg.body_width / 2
        half_h = pkg.body_length / 2

        # Draw body outline with chamfered corner for pin 1
        chamfer = min(1.0, half_w * 0.2, half_h * 0.2)

        # Start from top-left, going clockwise
        # Top edge (with chamfer at left)
        self.lines.append(Line(-half_w + chamfer, -half_h, half_w, -half_h, "F.Fab", width))
        # Right edge
        self.lines.append(Line(half_w, -half_h, half_w, half_h, "F.Fab", width))
        # Bottom edge
        self.lines.append(Line(half_w, half_h, -half_w, half_h, "F.Fab", width))
        # Left edge (with chamfer at top)
        self.lines.append(Line(-half_w, half_h, -half_w, -half_h + chamfer, "F.Fab", width))
        # Chamfer
        self.lines.append(
            Line(-half_w, -half_h + chamfer, -half_w + chamfer, -half_h, "F.Fab", width)
        )

    def add_reference_and_value(self) -> None:
        """Add reference designator and value text."""
        pkg = self.params.package

        # Reference above the component
        ref_y = -(pkg.body_length / 2 + 2.0)
        self.texts.append(
            Text("reference", "REF**", 0, ref_y, "F.SilkS", font_size=1.0, font_thickness=0.15)
        )

        # Value below the component (hidden on fab layer)
        val_y = pkg.body_length / 2 + 2.0
        self.texts.append(
            Text("value", self.params.footprint_name, 0, val_y, "F.Fab", font_size=1.0, hide=False)
        )

    def add_thermal_pad(self, thermal: ThermalPad) -> None:
        """Add exposed thermal pad with thermal vias.

        Args:
            thermal: Thermal pad configuration
        """
        # Main thermal pad (no paste - use subdivided paste apertures)
        self.pads.append(
            Pad(
                number=thermal.pin_number,
                pad_type=PadType.SMD,
                shape=PadShape.RECTANGLE,
                x=0,
                y=0,
                width=thermal.width,
                height=thermal.height,
                layers=["F.Cu", "F.Mask"],  # No paste on main pad
            )
        )

        # Add thermal vias if configured
        if thermal.total_via_count > 0:
            # Calculate via positions
            via_spacing_x = thermal.width / (thermal.via_count_x + 1)
            via_spacing_y = thermal.height / (thermal.via_count_y + 1)

            start_x = -thermal.width / 2 + via_spacing_x
            start_y = -thermal.height / 2 + via_spacing_y

            for i in range(thermal.via_count_x):
                for j in range(thermal.via_count_y):
                    via_x = start_x + i * via_spacing_x
                    via_y = start_y + j * via_spacing_y

                    self.pads.append(
                        Pad(
                            number=thermal.pin_number,
                            pad_type=PadType.THRU_HOLE,
                            shape=PadShape.CIRCLE,
                            x=via_x,
                            y=via_y,
                            width=thermal.via_pad_diameter,
                            height=thermal.via_pad_diameter,
                            drill=thermal.via_drill,
                            layers=["*.Cu"],
                            property_heatsink=True,
                        )
                    )

    def generate(self) -> str:
        """Generate the complete footprint file.

        Returns:
            KiCad footprint file content as string
        """
        # Clear any previous state
        self.pads.clear()
        self.lines.clear()
        self.circles.clear()
        self.arcs.clear()
        self.texts.clear()

        # Calculate all elements
        self.calculate_pads()
        self.calculate_silkscreen()
        self.calculate_courtyard()
        self.calculate_fab_layer()
        self.add_reference_and_value()

        # Add thermal pad if present
        if self.params.has_thermal_pad and self.params.thermal_pad:
            self.add_thermal_pad(self.params.thermal_pad)

        # Build output
        return self._build_sexpr()

    def _build_sexpr(self) -> str:
        """Build the S-expression output."""
        lines = []

        # Header
        lines.append(f'(footprint "{self.params.footprint_name}"')
        lines.append(f"  (version {KICAD_VERSION})")
        lines.append('  (generator "kiforge")')
        lines.append(f'  (generator_version "{datetime.now().strftime("%Y%m%d")}")')
        lines.append('  (layer "F.Cu")')

        # Description and tags
        if self.params.description:
            lines.append(f'  (descr "{self.params.description}")')
        if self.params.tags:
            lines.append(f'  (tags "{" ".join(self.params.tags)}")')

        # Attributes
        if self.params.pad_type == PadType.SMD:
            lines.append("  (attr smd)")
        elif self.params.pad_type == PadType.THRU_HOLE:
            lines.append("  (attr through_hole)")

        # Texts
        for text in self.texts:
            lines.append(self._format_text(text))

        # Graphics
        for line in self.lines:
            lines.append(self._format_line(line))
        for circle in self.circles:
            lines.append(self._format_circle(circle))
        for arc in self.arcs:
            lines.append(self._format_arc(arc))

        # Pads
        for pad in self.pads:
            lines.append(self._format_pad(pad))

        # 3D model
        if self.params.model_3d_path:
            lines.append(self._format_3d_model())

        lines.append(")")

        return "\n".join(lines)

    def _format_pad(self, pad: Pad) -> str:
        """Format a pad as S-expression."""
        parts = [f'  (pad "{pad.number}" {pad.pad_type.value} {pad.shape.value}']

        # Position
        if pad.rotation != 0:
            parts.append(f"    (at {pad.x:.4f} {pad.y:.4f} {pad.rotation})")
        else:
            parts.append(f"    (at {pad.x:.4f} {pad.y:.4f})")

        # Size
        parts.append(f"    (size {pad.width:.4f} {pad.height:.4f})")

        # Drill (for through-hole)
        if pad.drill is not None:
            if pad.drill_oval:
                parts.append(f"    (drill oval {pad.drill_oval[0]:.4f} {pad.drill_oval[1]:.4f})")
            else:
                parts.append(f"    (drill {pad.drill:.4f})")

        # Layers
        layer_str = " ".join(f'"{layer}"' for layer in pad.layers)
        parts.append(f"    (layers {layer_str})")

        # Roundrect ratio
        if pad.shape == PadShape.ROUNDRECT:
            parts.append(f"    (roundrect_rratio {pad.roundrect_ratio})")

        # Heatsink property
        if pad.property_heatsink:
            parts.append("    (property pad_prop_heatsink)")

        # UUID
        parts.append(f"    (uuid {uuid.uuid4()})")
        parts.append("  )")

        return "\n".join(parts)

    def _format_line(self, line: Line) -> str:
        """Format a line as S-expression."""
        return (
            f"  (fp_line\n"
            f"    (start {line.x1:.4f} {line.y1:.4f})\n"
            f"    (end {line.x2:.4f} {line.y2:.4f})\n"
            f'    (stroke (width {line.width}) (type solid))\n'
            f'    (layer "{line.layer}")\n'
            f"    (uuid {uuid.uuid4()})\n"
            f"  )"
        )

    def _format_circle(self, circle: Circle) -> str:
        """Format a circle as S-expression."""
        # KiCad uses center and a point on the edge
        edge_x = circle.cx + circle.radius
        edge_y = circle.cy
        fill = "solid" if circle.fill else "none"

        return (
            f"  (fp_circle\n"
            f"    (center {circle.cx:.4f} {circle.cy:.4f})\n"
            f"    (end {edge_x:.4f} {edge_y:.4f})\n"
            f'    (stroke (width {circle.width}) (type solid))\n'
            f"    (fill {fill})\n"
            f'    (layer "{circle.layer}")\n'
            f"    (uuid {uuid.uuid4()})\n"
            f"  )"
        )

    def _format_arc(self, arc: Arc) -> str:
        """Format an arc as S-expression."""
        return (
            f"  (fp_arc\n"
            f"    (start {arc.start_x:.4f} {arc.start_y:.4f})\n"
            f"    (mid {arc.mid_x:.4f} {arc.mid_y:.4f})\n"
            f"    (end {arc.end_x:.4f} {arc.end_y:.4f})\n"
            f'    (stroke (width {arc.width}) (type solid))\n'
            f'    (layer "{arc.layer}")\n'
            f"    (uuid {uuid.uuid4()})\n"
            f"  )"
        )

    def _format_text(self, text: Text) -> str:
        """Format text as S-expression."""
        hidden = " hide" if text.hide else ""
        return (
            f'  (fp_text {text.text_type} "{text.text}"\n'
            f"    (at {text.x:.4f} {text.y:.4f})\n"
            f'    (layer "{text.layer}"{hidden})\n'
            f"    (effects\n"
            f"      (font\n"
            f"        (size {text.font_size} {text.font_size})\n"
            f"        (thickness {text.font_thickness})\n"
            f"      )\n"
            f"    )\n"
            f"    (uuid {uuid.uuid4()})\n"
            f"  )"
        )

    def _format_3d_model(self) -> str:
        """Format 3D model reference as S-expression."""
        path = self.params.model_3d_path
        offset = self.params.model_3d_offset
        scale = self.params.model_3d_scale
        rotation = self.params.model_3d_rotation

        return (
            f'  (model "{path}"\n'
            f"    (offset (xyz {offset[0]} {offset[1]} {offset[2]}))\n"
            f"    (scale (xyz {scale[0]} {scale[1]} {scale[2]}))\n"
            f"    (rotate (xyz {rotation[0]} {rotation[1]} {rotation[2]}))\n"
            f"  )"
        )
