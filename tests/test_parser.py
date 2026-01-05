"""Tests for CSV parser and pin inference."""

import tempfile
from pathlib import Path

import pytest

from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle, PinGroupCategory
from kiforge.core.parser.inference import (
    infer_pin_electrical_type,
    infer_pin_graphic_style,
    infer_pin_group_category,
)
from kiforge.core.parser.csv_parser import parse_pinout_csv, create_component_from_csv


class TestPinTypeInference:
    """Tests for pin type inference from names."""

    def test_power_pins(self):
        assert infer_pin_electrical_type("VCC") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("VDD") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("AVDD") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("DVDD") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("VBAT") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("VIN") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("VCORE") == PinElectricalType.POWER_INPUT

    def test_ground_pins(self):
        assert infer_pin_electrical_type("GND") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("VSS") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("AGND") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("DGND") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("AVSS") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("PGND") == PinElectricalType.POWER_INPUT

    def test_nc_pins(self):
        assert infer_pin_electrical_type("NC") == PinElectricalType.NOT_CONNECTED
        assert infer_pin_electrical_type("N/C") == PinElectricalType.NOT_CONNECTED
        assert infer_pin_electrical_type("DNC") == PinElectricalType.NOT_CONNECTED
        assert infer_pin_electrical_type("RESERVED") == PinElectricalType.NOT_CONNECTED

    def test_clock_pins(self):
        assert infer_pin_electrical_type("CLK") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("CLOCK") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("CLKIN") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("OSC") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("XTAL") == PinElectricalType.INPUT

    def test_reset_pins(self):
        assert infer_pin_electrical_type("RST") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("RESET") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("NRST") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("MCLR") == PinElectricalType.INPUT

    def test_output_pins(self):
        assert infer_pin_electrical_type("OUT") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("TX") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("TXD") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("MOSI") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("SCK") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("DOUT") == PinElectricalType.OUTPUT
        assert infer_pin_electrical_type("TDO") == PinElectricalType.OUTPUT

    def test_input_pins(self):
        assert infer_pin_electrical_type("IN") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("RX") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("RXD") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("MISO") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("DIN") == PinElectricalType.INPUT
        assert infer_pin_electrical_type("TDI") == PinElectricalType.INPUT

    def test_gpio_pins(self):
        assert infer_pin_electrical_type("GPIO0") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("GPIO15") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("PA0") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("PB7") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("IO1") == PinElectricalType.BIDIRECTIONAL

    def test_bidirectional_pins(self):
        assert infer_pin_electrical_type("SDA") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("SWDIO") == PinElectricalType.BIDIRECTIONAL
        assert infer_pin_electrical_type("USB_DP") == PinElectricalType.BIDIRECTIONAL

    def test_open_drain_pins(self):
        # Note: INT matches "IN" pattern first, so it's classified as INPUT
        # Use full interrupt names or explicit OD suffix for open drain detection
        assert infer_pin_electrical_type("IRQ") == PinElectricalType.OPEN_COLLECTOR
        assert infer_pin_electrical_type("ALERT") == PinElectricalType.OPEN_COLLECTOR
        assert infer_pin_electrical_type("BUSY") == PinElectricalType.OPEN_COLLECTOR

    def test_analog_pins(self):
        assert infer_pin_electrical_type("AIN0") == PinElectricalType.PASSIVE
        assert infer_pin_electrical_type("ADC1") == PinElectricalType.PASSIVE
        assert infer_pin_electrical_type("VREF") == PinElectricalType.PASSIVE

    def test_unknown_pins(self):
        assert infer_pin_electrical_type("FOOBAR") == PinElectricalType.UNSPECIFIED
        assert infer_pin_electrical_type("X123") == PinElectricalType.UNSPECIFIED

    def test_case_insensitive(self):
        assert infer_pin_electrical_type("vcc") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("Gnd") == PinElectricalType.POWER_INPUT
        assert infer_pin_electrical_type("gpio0") == PinElectricalType.BIDIRECTIONAL


class TestPinGraphicStyleInference:
    """Tests for pin graphic style inference."""

    def test_inverted_pins(self):
        assert infer_pin_graphic_style("~RST") == PinGraphicStyle.INVERTED
        assert infer_pin_graphic_style("/CS") == PinGraphicStyle.INVERTED
        assert infer_pin_graphic_style("NRST") == PinGraphicStyle.INVERTED
        assert infer_pin_graphic_style("CS_N") == PinGraphicStyle.INVERTED
        assert infer_pin_graphic_style("OE_B") == PinGraphicStyle.INVERTED
        assert infer_pin_graphic_style("WR#") == PinGraphicStyle.INVERTED

    def test_clock_pins(self):
        assert infer_pin_graphic_style("CLK") == PinGraphicStyle.CLOCK
        assert infer_pin_graphic_style("CLOCK") == PinGraphicStyle.CLOCK
        assert infer_pin_graphic_style("SCK") == PinGraphicStyle.CLOCK
        assert infer_pin_graphic_style("SCLK") == PinGraphicStyle.CLOCK

    def test_normal_pins(self):
        assert infer_pin_graphic_style("VCC") == PinGraphicStyle.LINE
        assert infer_pin_graphic_style("GPIO0") == PinGraphicStyle.LINE
        assert infer_pin_graphic_style("TX") == PinGraphicStyle.LINE


class TestPinGroupCategoryInference:
    """Tests for pin group category inference."""

    def test_power_category(self):
        assert infer_pin_group_category("VCC", PinElectricalType.POWER_INPUT) == PinGroupCategory.POWER
        assert infer_pin_group_category("VDD", PinElectricalType.POWER_INPUT) == PinGroupCategory.POWER
        assert infer_pin_group_category("AVDD", PinElectricalType.POWER_INPUT) == PinGroupCategory.POWER

    def test_ground_category(self):
        assert infer_pin_group_category("GND", PinElectricalType.POWER_INPUT) == PinGroupCategory.GROUND
        assert infer_pin_group_category("VSS", PinElectricalType.POWER_INPUT) == PinGroupCategory.GROUND
        assert infer_pin_group_category("AGND", PinElectricalType.POWER_INPUT) == PinGroupCategory.GROUND

    def test_communication_category(self):
        assert infer_pin_group_category("SPI_MOSI", PinElectricalType.OUTPUT) == PinGroupCategory.COMMUNICATION
        assert infer_pin_group_category("I2C_SDA", PinElectricalType.BIDIRECTIONAL) == PinGroupCategory.COMMUNICATION
        assert infer_pin_group_category("UART_TX", PinElectricalType.OUTPUT) == PinGroupCategory.COMMUNICATION
        assert infer_pin_group_category("MOSI", PinElectricalType.OUTPUT) == PinGroupCategory.COMMUNICATION

    def test_debug_category(self):
        assert infer_pin_group_category("TDI", PinElectricalType.INPUT) == PinGroupCategory.DEBUG
        assert infer_pin_group_category("TDO", PinElectricalType.OUTPUT) == PinGroupCategory.DEBUG
        assert infer_pin_group_category("SWDIO", PinElectricalType.BIDIRECTIONAL) == PinGroupCategory.DEBUG
        assert infer_pin_group_category("SWCLK", PinElectricalType.INPUT) == PinGroupCategory.DEBUG

    def test_clock_category(self):
        assert infer_pin_group_category("CLK", PinElectricalType.INPUT) == PinGroupCategory.CLOCK
        assert infer_pin_group_category("XTAL_IN", PinElectricalType.INPUT) == PinGroupCategory.CLOCK

    def test_control_category(self):
        assert infer_pin_group_category("EN", PinElectricalType.INPUT) == PinGroupCategory.CONTROL
        assert infer_pin_group_category("RESET", PinElectricalType.INPUT) == PinGroupCategory.CONTROL
        assert infer_pin_group_category("CS", PinElectricalType.INPUT) == PinGroupCategory.CONTROL

    def test_nc_category(self):
        assert infer_pin_group_category("NC", PinElectricalType.NOT_CONNECTED) == PinGroupCategory.NC


class TestCSVParser:
    """Tests for CSV pinout parser."""

    def test_parse_basic_csv(self):
        csv_content = """pin,name,type
1,VCC,power
2,GND,gnd
3,IO1,io
4,IO2,io
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert len(pins) == 4
        assert pins[0].number == "1"
        assert pins[0].name == "VCC"
        assert pins[0].electrical_type == PinElectricalType.POWER_INPUT
        assert pins[1].name == "GND"
        assert pins[2].electrical_type == PinElectricalType.BIDIRECTIONAL

    def test_parse_csv_with_alternate_column_names(self):
        csv_content = """Pin Number,Signal Name,Direction
1,VCC,Power
2,GND,Ground
3,DATA,I/O
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert len(pins) == 3
        assert pins[0].number == "1"
        assert pins[0].name == "VCC"

    def test_parse_csv_infers_types_when_missing(self):
        csv_content = """pin,name
1,VCC
2,GND
3,GPIO0
4,TX
5,RX
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert pins[0].electrical_type == PinElectricalType.POWER_INPUT  # VCC
        assert pins[1].electrical_type == PinElectricalType.POWER_INPUT  # GND
        assert pins[2].electrical_type == PinElectricalType.BIDIRECTIONAL  # GPIO0
        assert pins[3].electrical_type == PinElectricalType.OUTPUT  # TX
        assert pins[4].electrical_type == PinElectricalType.INPUT  # RX

    def test_parse_csv_with_description(self):
        csv_content = """pin,name,type,description
1,VCC,power,Main power supply
2,GPIO0,io,General purpose I/O
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert pins[0].description == "Main power supply"
        assert pins[1].description == "General purpose I/O"

    def test_parse_csv_with_alternates(self):
        csv_content = """pin,name,type,alternate
1,PA0,io,"SPI_MOSI, TIM1_CH1"
2,PA1,io,SPI_MISO
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert pins[0].alternate_names == ["SPI_MOSI", "TIM1_CH1"]
        assert pins[1].alternate_names == ["SPI_MISO"]

    def test_parse_csv_skips_empty_rows(self):
        csv_content = """pin,name
1,VCC

2,GND

3,IO1
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert len(pins) == 3

    def test_parse_csv_handles_semicolon_delimiter(self):
        csv_content = """pin;name;type
1;VCC;power
2;GND;gnd
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert len(pins) == 2
        assert pins[0].name == "VCC"

    def test_parse_csv_missing_required_column_fails(self):
        csv_content = """name,type
VCC,power
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            with pytest.raises(ValueError, match="pin number"):
                parse_pinout_csv(f.name)

    def test_parse_csv_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_pinout_csv("/nonexistent/path/file.csv")

    def test_create_component_from_csv(self):
        csv_content = """pin,name,type
1,VCC,power
2,GND,gnd
3,IO1,io
4,IO2,io
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            component = create_component_from_csv(
                f.name,
                component_name="TEST_CHIP",
                manufacturer="ACME",
                description="Test component",
            )

        assert component.name == "TEST_CHIP"
        assert component.manufacturer == "ACME"
        assert component.description == "Test component"
        assert component.pin_count == 4

    def test_parse_csv_type_mappings(self):
        csv_content = """pin,name,type
1,A,i
2,B,o
3,C,io
4,D,p
5,E,nc
6,F,tristate
7,G,od
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            pins = parse_pinout_csv(f.name)

        assert pins[0].electrical_type == PinElectricalType.INPUT
        assert pins[1].electrical_type == PinElectricalType.OUTPUT
        assert pins[2].electrical_type == PinElectricalType.BIDIRECTIONAL
        assert pins[3].electrical_type == PinElectricalType.POWER_INPUT
        assert pins[4].electrical_type == PinElectricalType.NOT_CONNECTED
        assert pins[5].electrical_type == PinElectricalType.TRISTATE
        assert pins[6].electrical_type == PinElectricalType.OPEN_COLLECTOR
