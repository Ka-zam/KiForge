"""KiCad schematic symbol generator."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from kiforge.core.models.component import ComponentInfo
from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle, PinOrientation
from kiforge.core.models.pin import Pin

# KiCad 8 format version (YYYYMMDD)
KICAD_VERSION = 20241229

# Standard symbol dimensions
PIN_LENGTH = 2.54  # 100 mils
PIN_SPACING = 2.54  # 100 mils (1 grid unit)
FONT_SIZE = 1.27  # 50 mils
LINE_WIDTH = 0.254  # 10 mils


@dataclass
class SymbolPin:
    """Internal representation of a symbol pin for layout."""

    pin: Pin
    x: float = 0.0
    y: float = 0.0
    orientation: PinOrientation = PinOrientation.RIGHT


@dataclass
class SymbolLayout:
    """Layout information for a symbol unit."""

    unit: int = 1
    width: float = 10.16  # Default 400 mils
    height: float = 10.16
    left_pins: list[SymbolPin] = field(default_factory=list)
    right_pins: list[SymbolPin] = field(default_factory=list)
    top_pins: list[SymbolPin] = field(default_factory=list)
    bottom_pins: list[SymbolPin] = field(default_factory=list)


class SymbolGenerator:
    """Generator for KiCad schematic symbols.

    Creates .kicad_sym files with proper pin placement, properties,
    and graphical elements.
    """

    def __init__(self, component: ComponentInfo):
        """Initialize the generator.

        Args:
            component: Component information with pins
        """
        self.component = component
        self.layouts: list[SymbolLayout] = []

    def layout_pins(self) -> None:
        """Calculate pin positions for the symbol.

        Organizes pins by type:
        - Power (VCC, VDD) on top
        - Ground (GND, VSS) on bottom
        - Inputs on left
        - Outputs on right
        - Bidirectional distributed
        """
        # Group pins by category
        power_pins = []
        ground_pins = []
        input_pins = []
        output_pins = []
        bidir_pins = []
        nc_pins = []
        other_pins = []

        for pin in self.component.pins:
            if pin.is_ground:
                ground_pins.append(pin)
            elif pin.is_supply:
                power_pins.append(pin)
            elif pin.electrical_type == PinElectricalType.INPUT:
                input_pins.append(pin)
            elif pin.electrical_type == PinElectricalType.OUTPUT:
                output_pins.append(pin)
            elif pin.electrical_type == PinElectricalType.BIDIRECTIONAL:
                bidir_pins.append(pin)
            elif pin.electrical_type == PinElectricalType.NOT_CONNECTED:
                nc_pins.append(pin)
            else:
                other_pins.append(pin)

        # Sort pins within each category by name for consistent ordering
        for pin_list in [power_pins, ground_pins, input_pins, output_pins, bidir_pins, nc_pins, other_pins]:
            pin_list.sort(key=lambda p: (p.name, p.number))

        # Distribute bidirectional pins between left and right
        left_bidir = bidir_pins[: len(bidir_pins) // 2]
        right_bidir = bidir_pins[len(bidir_pins) // 2 :]

        # Combine pins for each side
        left_side = input_pins + left_bidir + other_pins
        right_side = output_pins + right_bidir
        top_side = power_pins
        bottom_side = ground_pins + nc_pins

        # Calculate symbol dimensions
        max_side_pins = max(len(left_side), len(right_side), 1)
        max_tb_pins = max(len(top_side), len(bottom_side), 1)

        # Symbol body size (in mm, rounded to grid)
        height = max(max_side_pins * PIN_SPACING + 2 * PIN_SPACING, 10.16)
        width = max(max_tb_pins * PIN_SPACING + 4 * PIN_SPACING, 10.16)

        # Round to grid
        height = round(height / PIN_SPACING) * PIN_SPACING
        width = round(width / PIN_SPACING) * PIN_SPACING

        layout = SymbolLayout(unit=1, width=width, height=height)

        # Position left pins (connection on left, pointing into symbol from left)
        y_start = (len(left_side) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(left_side):
            y = y_start - i * PIN_SPACING
            layout.left_pins.append(
                SymbolPin(pin=pin, x=-width / 2 - PIN_LENGTH, y=y, orientation=PinOrientation.RIGHT)
            )

        # Position right pins (connection on right, pointing into symbol from right)
        y_start = (len(right_side) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(right_side):
            y = y_start - i * PIN_SPACING
            layout.right_pins.append(
                SymbolPin(pin=pin, x=width / 2 + PIN_LENGTH, y=y, orientation=PinOrientation.LEFT)
            )

        # Position top pins (connection on top, pointing down into symbol)
        x_start = -(len(top_side) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(top_side):
            x = x_start + i * PIN_SPACING
            layout.top_pins.append(
                SymbolPin(pin=pin, x=x, y=height / 2 + PIN_LENGTH, orientation=PinOrientation.DOWN)
            )

        # Position bottom pins (connection on bottom, pointing up into symbol)
        x_start = -(len(bottom_side) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(bottom_side):
            x = x_start + i * PIN_SPACING
            layout.bottom_pins.append(
                SymbolPin(pin=pin, x=x, y=-height / 2 - PIN_LENGTH, orientation=PinOrientation.UP)
            )

        self.layouts = [layout]

    def generate(self) -> str:
        """Generate the complete symbol library file.

        Returns:
            KiCad symbol library file content
        """
        # Calculate layout
        self.layout_pins()

        # Build output
        lines = []

        # Library header
        lines.append("(kicad_symbol_lib")
        lines.append(f"  (version {KICAD_VERSION})")
        lines.append('  (generator "kiforge")')
        lines.append(f'  (generator_version "{datetime.now().strftime("%Y%m%d")}")')
        lines.append("")

        # Symbol definition
        lines.append(self._generate_symbol())

        lines.append(")")

        return "\n".join(lines)

    def _generate_symbol(self) -> str:
        """Generate the symbol definition."""
        lines = []
        name = self.component.name

        lines.append(f'  (symbol "{name}"')
        lines.append("    (exclude_from_sim no)")
        lines.append("    (in_bom yes)")
        lines.append("    (on_board yes)")

        # Properties
        lines.append(self._generate_properties())

        # Generate shared graphics (unit 0, style 1)
        lines.append(self._generate_body_graphics())

        # Generate pins for each unit
        for layout in self.layouts:
            lines.append(self._generate_unit_pins(layout))

        lines.append("  )")

        return "\n".join(lines)

    def _generate_properties(self) -> str:
        """Generate symbol properties."""
        lines = []
        comp = self.component
        layout = self.layouts[0] if self.layouts else SymbolLayout()

        # Reference - top left of symbol
        ref_x = -layout.width / 2
        ref_y = layout.height / 2 + 1.27
        lines.append(
            f'    (property "Reference" "{comp.reference_prefix}"'
            f"\n      (at {ref_x:.2f} {ref_y:.2f} 0)"
            f"\n      (effects (font (size {FONT_SIZE} {FONT_SIZE})) (justify left))"
            f"\n    )"
        )

        # Value - below reference
        val_y = ref_y - 2.54
        lines.append(
            f'    (property "Value" "{comp.name}"'
            f"\n      (at {ref_x:.2f} {val_y:.2f} 0)"
            f"\n      (effects (font (size {FONT_SIZE} {FONT_SIZE})) (justify left))"
            f"\n    )"
        )

        # Footprint
        footprint = ""
        if comp.primary_package:
            footprint = f"KiForge:{comp.primary_package.generate_ipc_name()}"
        lines.append(
            f'    (property "Footprint" "{footprint}"'
            f"\n      (at 0 0 0)"
            f"\n      (effects (font (size {FONT_SIZE} {FONT_SIZE})) hide)"
            f"\n    )"
        )

        # Datasheet
        datasheet = comp.datasheet_url or ""
        lines.append(
            f'    (property "Datasheet" "{datasheet}"'
            f"\n      (at 0 0 0)"
            f"\n      (effects (font (size {FONT_SIZE} {FONT_SIZE})) hide)"
            f"\n    )"
        )

        # Description
        lines.append(
            f'    (property "Description" "{comp.description}"'
            f"\n      (at 0 0 0)"
            f"\n      (effects (font (size {FONT_SIZE} {FONT_SIZE})) hide)"
            f"\n    )"
        )

        return "\n".join(lines)

    def _generate_body_graphics(self) -> str:
        """Generate the symbol body rectangle (shared across units)."""
        lines = []
        layout = self.layouts[0] if self.layouts else SymbolLayout()
        name = self.component.name

        # Unit 0 = shared graphics, Style 1 = normal
        lines.append(f'    (symbol "{name}_0_1"')

        # Body rectangle
        x1 = -layout.width / 2
        y1 = layout.height / 2
        x2 = layout.width / 2
        y2 = -layout.height / 2

        lines.append(
            f"      (rectangle (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f})"
            f"\n        (stroke (width {LINE_WIDTH}) (type default))"
            f"\n        (fill (type background))"
            f"\n      )"
        )

        lines.append("    )")

        return "\n".join(lines)

    def _generate_unit_pins(self, layout: SymbolLayout) -> str:
        """Generate pins for a symbol unit."""
        lines = []
        name = self.component.name

        # Unit N, Style 1
        lines.append(f'    (symbol "{name}_{layout.unit}_1"')

        # All pins from all sides
        all_pins = layout.left_pins + layout.right_pins + layout.top_pins + layout.bottom_pins

        for sym_pin in all_pins:
            lines.append(self._generate_pin(sym_pin))

        lines.append("    )")

        return "\n".join(lines)

    def _generate_pin(self, sym_pin: SymbolPin) -> str:
        """Generate a single pin definition."""
        pin = sym_pin.pin
        etype = pin.electrical_type.value
        gstyle = pin.graphic_style.value

        # Pin angle based on orientation
        angle = sym_pin.orientation.value

        # Escape special characters in pin name
        pin_name = pin.name.replace('"', '\\"')

        lines = [
            f"      (pin {etype} {gstyle}",
            f"        (at {sym_pin.x:.2f} {sym_pin.y:.2f} {angle})",
            f"        (length {PIN_LENGTH})",
            f'        (name "{pin_name}" (effects (font (size {FONT_SIZE} {FONT_SIZE}))))',
            f'        (number "{pin.number}" (effects (font (size {FONT_SIZE} {FONT_SIZE}))))',
            "      )",
        ]

        return "\n".join(lines)


def create_symbol(component: ComponentInfo) -> str:
    """Create a KiCad symbol for a component.

    Args:
        component: Component information

    Returns:
        KiCad symbol library file content
    """
    generator = SymbolGenerator(component)
    return generator.generate()
