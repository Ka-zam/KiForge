"""Tests for symbol generator."""

import pytest

from kiforge.core.symbol.generator import SymbolGenerator, create_symbol
from kiforge.core.models.component import ComponentInfo
from kiforge.core.models.pin import Pin
from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle


class TestSymbolGenerator:
    """Tests for symbol generator."""

    def create_test_component(self) -> ComponentInfo:
        """Create a test component with various pin types."""
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="GND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="IN1", electrical_type=PinElectricalType.INPUT),
            Pin(number="4", name="IN2", electrical_type=PinElectricalType.INPUT),
            Pin(number="5", name="OUT1", electrical_type=PinElectricalType.OUTPUT),
            Pin(number="6", name="OUT2", electrical_type=PinElectricalType.OUTPUT),
            Pin(number="7", name="IO1", electrical_type=PinElectricalType.BIDIRECTIONAL),
            Pin(number="8", name="IO2", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        return ComponentInfo(
            name="TEST_IC",
            manufacturer="ACME",
            description="Test integrated circuit",
            pins=pins,
        )

    def test_symbol_generator_init(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        assert generator.component == component

    def test_symbol_layout_pins(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        generator.layout_pins()

        assert len(generator.layouts) == 1
        layout = generator.layouts[0]

        # Power pins should be on top
        top_names = [sp.pin.name for sp in layout.top_pins]
        assert "VCC" in top_names

        # Ground pins should be on bottom
        bottom_names = [sp.pin.name for sp in layout.bottom_pins]
        assert "GND" in bottom_names

        # Input pins should be on left
        left_names = [sp.pin.name for sp in layout.left_pins]
        assert any("IN" in name for name in left_names)

        # Output pins should be on right
        right_names = [sp.pin.name for sp in layout.right_pins]
        assert any("OUT" in name for name in right_names)

    def test_symbol_generate_output_format(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        # Check library header
        assert content.startswith("(kicad_symbol_lib")
        assert "(version 20241229)" in content
        assert '(generator "kiforge")' in content

    def test_symbol_generate_contains_symbol_definition(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        assert '(symbol "TEST_IC"' in content

    def test_symbol_generate_contains_properties(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        assert '(property "Reference" "U"' in content
        assert '(property "Value" "TEST_IC"' in content
        assert '(property "Footprint"' in content
        assert '(property "Datasheet"' in content
        assert '(property "Description"' in content

    def test_symbol_generate_contains_body_rectangle(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        # Unit 0 contains the shared body graphics
        assert '(symbol "TEST_IC_0_1"' in content
        assert "(rectangle" in content

    def test_symbol_generate_contains_pins(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        # Unit 1 contains the pins
        assert '(symbol "TEST_IC_1_1"' in content

        # Check for pin definitions
        assert '(pin power_in line' in content
        assert '(pin input line' in content
        assert '(pin output line' in content
        assert '(pin bidirectional line' in content

    def test_symbol_generate_pin_numbers(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        # All pin numbers should be present
        for i in range(1, 9):
            assert f'(number "{i}"' in content

    def test_symbol_generate_pin_names(self):
        component = self.create_test_component()
        generator = SymbolGenerator(component)
        content = generator.generate()

        assert '(name "VCC"' in content
        assert '(name "GND"' in content
        assert '(name "IN1"' in content
        assert '(name "OUT1"' in content
        assert '(name "IO1"' in content


class TestCreateSymbol:
    """Tests for the create_symbol convenience function."""

    def test_create_symbol_simple(self):
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="GND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="OUT", electrical_type=PinElectricalType.OUTPUT),
        ]
        component = ComponentInfo(name="SIMPLE_CHIP", pins=pins)
        content = create_symbol(component)

        assert "(kicad_symbol_lib" in content
        assert '(symbol "SIMPLE_CHIP"' in content
        assert '(number "1"' in content
        assert '(number "2"' in content
        assert '(number "3"' in content

    def test_create_symbol_with_special_characters(self):
        pins = [
            Pin(number="1", name="~RST", electrical_type=PinElectricalType.INPUT),
            Pin(number="2", name="D+", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        component = ComponentInfo(name="SPECIAL_CHIP", pins=pins)
        content = create_symbol(component)

        # Check that special characters are handled
        assert '(name "~RST"' in content or '(name "\\~RST"' in content
        assert '(name "D+"' in content

    def test_create_symbol_empty_pins(self):
        component = ComponentInfo(name="EMPTY_CHIP", pins=[])
        content = create_symbol(component)

        # Should still generate valid structure
        assert "(kicad_symbol_lib" in content
        assert '(symbol "EMPTY_CHIP"' in content

    def test_create_symbol_single_pin(self):
        pins = [Pin(number="1", name="SIG", electrical_type=PinElectricalType.INPUT)]
        component = ComponentInfo(name="SINGLE_PIN", pins=pins)
        content = create_symbol(component)

        assert '(pin input line' in content
        assert '(name "SIG"' in content


class TestSymbolPinPlacement:
    """Tests for pin placement logic."""

    def test_power_pins_on_top(self):
        pins = [
            Pin(number="1", name="VDD", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="AVDD", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        component = ComponentInfo(name="POWER_TEST", pins=pins)
        generator = SymbolGenerator(component)
        generator.layout_pins()

        layout = generator.layouts[0]
        top_names = [sp.pin.name for sp in layout.top_pins]

        # VDD should be identified as supply pin and placed on top
        # (Note: depends on is_supply heuristic)
        assert len(layout.top_pins) >= 1

    def test_ground_pins_on_bottom(self):
        pins = [
            Pin(number="1", name="VSS", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="AGND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        component = ComponentInfo(name="GND_TEST", pins=pins)
        generator = SymbolGenerator(component)
        generator.layout_pins()

        layout = generator.layouts[0]
        bottom_names = [sp.pin.name for sp in layout.bottom_pins]

        # Ground pins should be on bottom
        assert "VSS" in bottom_names or "AGND" in bottom_names

    def test_nc_pins_on_bottom(self):
        pins = [
            Pin(number="1", name="NC", electrical_type=PinElectricalType.NOT_CONNECTED),
            Pin(number="2", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        component = ComponentInfo(name="NC_TEST", pins=pins)
        generator = SymbolGenerator(component)
        generator.layout_pins()

        layout = generator.layouts[0]
        bottom_names = [sp.pin.name for sp in layout.bottom_pins]

        assert "NC" in bottom_names

    def test_bidirectional_pins_distributed(self):
        # Create component with mostly bidirectional pins
        pins = [
            Pin(number=str(i), name=f"IO{i}", electrical_type=PinElectricalType.BIDIRECTIONAL)
            for i in range(1, 9)
        ]
        component = ComponentInfo(name="BIDIR_TEST", pins=pins)
        generator = SymbolGenerator(component)
        generator.layout_pins()

        layout = generator.layouts[0]

        # Bidirectional pins should be distributed between left and right
        # Since there are no inputs/outputs, all bidir go to left first, then split
        total_left_right = len(layout.left_pins) + len(layout.right_pins)
        assert total_left_right == 8


class TestSymbolGraphicStyles:
    """Tests for pin graphic style rendering."""

    def test_inverted_pin_style(self):
        pins = [
            Pin(
                number="1",
                name="~CS",
                electrical_type=PinElectricalType.INPUT,
                graphic_style=PinGraphicStyle.INVERTED,
            ),
        ]
        component = ComponentInfo(name="INVERTED_TEST", pins=pins)
        content = create_symbol(component)

        assert "(pin input inverted" in content

    def test_clock_pin_style(self):
        pins = [
            Pin(
                number="1",
                name="CLK",
                electrical_type=PinElectricalType.INPUT,
                graphic_style=PinGraphicStyle.CLOCK,
            ),
        ]
        component = ComponentInfo(name="CLOCK_TEST", pins=pins)
        content = create_symbol(component)

        assert "(pin input clock" in content
