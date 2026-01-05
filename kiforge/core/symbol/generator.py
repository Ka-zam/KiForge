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
    name: str = ""  # Unit name (e.g., "Bank 0", "JTAG")
    width: float = 10.16  # Default 400 mils
    height: float = 10.16
    left_pins: list[SymbolPin] = field(default_factory=list)
    right_pins: list[SymbolPin] = field(default_factory=list)
    top_pins: list[SymbolPin] = field(default_factory=list)
    bottom_pins: list[SymbolPin] = field(default_factory=list)
    is_power_unit: bool = False  # If True, unit contains only power/ground pins


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

        For single-unit symbols, organizes pins by type:
        - Power (VCC, VDD) on top
        - Ground (GND, VSS) on bottom
        - Inputs on left
        - Outputs on right
        - Bidirectional distributed

        For multi-unit symbols, creates separate layouts per unit.
        """
        # Check if this is a multi-unit symbol
        units = set(pin.unit for pin in self.component.pins)

        if len(units) <= 1:
            # Single unit - use simple layout
            self._layout_single_unit(self.component.pins, unit=1)
        else:
            # Multi-unit - layout each unit separately
            self._layout_multi_unit(units)

    def _layout_single_unit(self, pins: list[Pin], unit: int = 1, unit_name: str = "") -> None:
        """Layout pins for a single unit.

        Args:
            pins: Pins to layout
            unit: Unit number
            unit_name: Optional unit name for labeling
        """
        # Group pins by category
        power_pins = []
        ground_pins = []
        input_pins = []
        output_pins = []
        bidir_pins = []
        nc_pins = []
        other_pins = []

        for pin in pins:
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

        # Check if this is a power-only unit
        is_power = len(power_pins) + len(ground_pins) == len(pins) and len(pins) > 0

        layout = SymbolLayout(
            unit=unit,
            name=unit_name,
            width=width,
            height=height,
            is_power_unit=is_power,
        )

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

        self.layouts.append(layout)

    def _layout_multi_unit(self, units: set[int]) -> None:
        """Layout pins for a multi-unit symbol.

        Args:
            units: Set of unit numbers present in the component
        """
        # Try to import unit names from FPGA parser if available
        try:
            from kiforge.core.parser.fpga_csv_parser import get_fpga_unit_names
            unit_names = get_fpga_unit_names()
        except ImportError:
            unit_names = {}

        # Sort units for consistent ordering
        sorted_units = sorted(units)

        # Layout each unit
        for unit_num in sorted_units:
            unit_pins = [p for p in self.component.pins if p.unit == unit_num]
            if not unit_pins:
                continue

            unit_name = unit_names.get(unit_num, f"Unit {unit_num}")
            self._layout_unit_pins(unit_pins, unit_num, unit_name)

    def _layout_unit_pins(self, pins: list[Pin], unit: int, unit_name: str = "") -> None:
        """Layout pins for a specific unit with FPGA-aware organization.

        For I/O bank units, groups differential pairs together.
        For power units, stacks power on top and ground on bottom.

        Args:
            pins: Pins for this unit
            unit: Unit number
            unit_name: Human-readable unit name
        """
        # Separate power/ground from signal pins
        power_pins = [p for p in pins if p.is_supply]
        ground_pins = [p for p in pins if p.is_ground]
        nc_pins = [p for p in pins if p.is_nc]
        signal_pins = [p for p in pins if not (p.is_supply or p.is_ground or p.is_nc)]

        # Sort power pins by name
        power_pins.sort(key=lambda p: p.name)
        ground_pins.sort(key=lambda p: p.name)

        # For signal pins, try to keep differential pairs together
        signal_pins = self._sort_with_diff_pairs(signal_pins)

        # Distribute signal pins between left and right sides
        # Put positive diff pins and inputs on left, negative and outputs on right
        left_signals = []
        right_signals = []

        for pin in signal_pins:
            name = pin.name.upper()
            # Positive differential or input-like
            if name.endswith("P") or name.endswith("A") or pin.electrical_type == PinElectricalType.INPUT:
                left_signals.append(pin)
            # Negative differential or output-like
            elif name.endswith("N") or name.endswith("B") or pin.electrical_type == PinElectricalType.OUTPUT:
                right_signals.append(pin)
            else:
                # Distribute evenly
                if len(left_signals) <= len(right_signals):
                    left_signals.append(pin)
                else:
                    right_signals.append(pin)

        # Calculate dimensions
        max_side = max(len(left_signals), len(right_signals), 1)
        max_tb = max(len(power_pins), len(ground_pins) + len(nc_pins), 1)

        height = max(max_side * PIN_SPACING + 2 * PIN_SPACING, 10.16)
        width = max(max_tb * PIN_SPACING + 4 * PIN_SPACING, 10.16)

        # Round to grid
        height = round(height / PIN_SPACING) * PIN_SPACING
        width = round(width / PIN_SPACING) * PIN_SPACING

        # Check if power-only unit
        is_power = len(signal_pins) == 0 and (len(power_pins) > 0 or len(ground_pins) > 0)

        layout = SymbolLayout(
            unit=unit,
            name=unit_name,
            width=width,
            height=height,
            is_power_unit=is_power,
        )

        # Position pins
        # Left side
        y_start = (len(left_signals) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(left_signals):
            y = y_start - i * PIN_SPACING
            layout.left_pins.append(
                SymbolPin(pin=pin, x=-width / 2 - PIN_LENGTH, y=y, orientation=PinOrientation.RIGHT)
            )

        # Right side
        y_start = (len(right_signals) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(right_signals):
            y = y_start - i * PIN_SPACING
            layout.right_pins.append(
                SymbolPin(pin=pin, x=width / 2 + PIN_LENGTH, y=y, orientation=PinOrientation.LEFT)
            )

        # Top (power)
        x_start = -(len(power_pins) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(power_pins):
            x = x_start + i * PIN_SPACING
            layout.top_pins.append(
                SymbolPin(pin=pin, x=x, y=height / 2 + PIN_LENGTH, orientation=PinOrientation.DOWN)
            )

        # Bottom (ground + NC)
        bottom_pins = ground_pins + nc_pins
        x_start = -(len(bottom_pins) - 1) * PIN_SPACING / 2
        for i, pin in enumerate(bottom_pins):
            x = x_start + i * PIN_SPACING
            layout.bottom_pins.append(
                SymbolPin(pin=pin, x=x, y=-height / 2 - PIN_LENGTH, orientation=PinOrientation.UP)
            )

        self.layouts.append(layout)

    def _sort_with_diff_pairs(self, pins: list[Pin]) -> list[Pin]:
        """Sort pins keeping differential pairs adjacent.

        Pairs are identified by matching names with P/N or A/B suffixes.

        Args:
            pins: List of pins to sort

        Returns:
            Sorted list with pairs adjacent
        """
        import re

        # Build a map of base names to pins
        pairs: dict[str, list[Pin]] = {}
        singles: list[Pin] = []

        for pin in pins:
            name = pin.name.upper()
            # Check for differential pair naming
            match = re.match(r"(.+?)([PN]|[AB])$", name)
            if match:
                base = match.group(1)
                if base not in pairs:
                    pairs[base] = []
                pairs[base].append(pin)
            else:
                singles.append(pin)

        # Build sorted output: pairs first (P before N), then singles
        result = []
        for base in sorted(pairs.keys()):
            pair_pins = pairs[base]
            # Sort so P/A comes before N/B
            pair_pins.sort(key=lambda p: (0 if p.name.upper().endswith(("P", "A")) else 1, p.name))
            result.extend(pair_pins)

        # Add singles, sorted by name
        singles.sort(key=lambda p: p.name)
        result.extend(singles)

        return result

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

        # Multi-unit symbols need special flags
        if len(self.layouts) > 1:
            lines.append("    (pin_numbers hide)")
            lines.append("    (pin_names (offset 1.016))")

        lines.append("    (exclude_from_sim no)")
        lines.append("    (in_bom yes)")
        lines.append("    (on_board yes)")

        # Properties
        lines.append(self._generate_properties())

        # For multi-unit, each unit has its own body
        if len(self.layouts) > 1:
            # Generate per-unit graphics and pins
            for layout in self.layouts:
                lines.append(self._generate_unit_body(layout))
                lines.append(self._generate_unit_pins(layout))
        else:
            # Single unit - shared graphics
            lines.append(self._generate_body_graphics())
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

    def _generate_unit_body(self, layout: SymbolLayout) -> str:
        """Generate body graphics for a specific unit (multi-unit symbols)."""
        lines = []
        name = self.component.name

        # Unit N, Style 0 = unit-specific graphics
        lines.append(f'    (symbol "{name}_{layout.unit}_0"')

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

        # Add unit name label inside the rectangle
        if layout.name:
            label_y = y1 - 1.27  # Just below top edge
            lines.append(
                f'      (text "{layout.name}"'
                f"\n        (at 0 {label_y:.2f} 0)"
                f"\n        (effects (font (size {FONT_SIZE} {FONT_SIZE})))"
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
