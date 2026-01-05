"""Tests for data models."""

import pytest
from pydantic import ValidationError

from kiforge.core.models.enums import (
    PackageType,
    PadShape,
    PinElectricalType,
    PinGraphicStyle,
    PinGroupCategory,
)
from kiforge.core.models.pin import Pin, PinGroup
from kiforge.core.models.package import PackageInfo, ThermalPad, QFPParams, QFNParams, BGAParams
from kiforge.core.models.component import ComponentInfo


class TestPin:
    """Tests for Pin model."""

    def test_create_basic_pin(self):
        pin = Pin(number="1", name="VCC")
        assert pin.number == "1"
        assert pin.name == "VCC"
        assert pin.electrical_type == PinElectricalType.UNSPECIFIED
        assert pin.graphic_style == PinGraphicStyle.LINE

    def test_create_pin_with_all_fields(self):
        pin = Pin(
            number="A1",
            name="GPIO0",
            electrical_type=PinElectricalType.BIDIRECTIONAL,
            graphic_style=PinGraphicStyle.LINE,
            alternate_names=["SPI_MOSI", "UART_TX"],
            row="A",
            column=1,
            unit=1,
            description="General purpose I/O",
        )
        assert pin.number == "A1"
        assert pin.alternate_names == ["SPI_MOSI", "UART_TX"]
        assert pin.row == "A"
        assert pin.column == 1

    def test_pin_strips_whitespace(self):
        pin = Pin(number="  1  ", name="  VCC  ")
        assert pin.number == "1"
        assert pin.name == "VCC"

    def test_pin_empty_number_fails(self):
        with pytest.raises(ValidationError):
            Pin(number="", name="VCC")

    def test_pin_empty_name_fails(self):
        with pytest.raises(ValidationError):
            Pin(number="1", name="")

    def test_pin_is_power(self):
        power_pin = Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT)
        assert power_pin.is_power is True

        io_pin = Pin(number="2", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL)
        assert io_pin.is_power is False

    def test_pin_is_ground(self):
        gnd_pin = Pin(number="1", name="GND")
        assert gnd_pin.is_ground is True

        vss_pin = Pin(number="2", name="AVSS")
        assert vss_pin.is_ground is True

        vcc_pin = Pin(number="3", name="VCC")
        assert vcc_pin.is_ground is False

    def test_pin_is_supply(self):
        vcc_pin = Pin(number="1", name="VCC")
        assert vcc_pin.is_supply is True

        vdd_pin = Pin(number="2", name="AVDD")
        assert vdd_pin.is_supply is True

        gnd_pin = Pin(number="3", name="GND")
        assert gnd_pin.is_supply is False

    def test_pin_is_nc(self):
        nc_pin = Pin(number="1", name="NC", electrical_type=PinElectricalType.NOT_CONNECTED)
        assert nc_pin.is_nc is True

        io_pin = Pin(number="2", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL)
        assert io_pin.is_nc is False

    def test_pin_is_immutable(self):
        pin = Pin(number="1", name="VCC")
        with pytest.raises(ValidationError):
            pin.number = "2"


class TestPinGroup:
    """Tests for PinGroup model."""

    def test_create_pin_group(self):
        pins = [
            Pin(number="1", name="VCC"),
            Pin(number="2", name="VDD"),
        ]
        group = PinGroup(name="Power", category=PinGroupCategory.POWER, pins=pins)
        assert group.name == "Power"
        assert group.pin_count == 2
        assert group.category == PinGroupCategory.POWER

    def test_pin_group_get_pins_by_type(self):
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="IO", electrical_type=PinElectricalType.BIDIRECTIONAL),
            Pin(number="3", name="VDD", electrical_type=PinElectricalType.POWER_INPUT),
        ]
        group = PinGroup(name="Mixed", pins=pins)

        power_pins = group.get_pins_by_type(PinElectricalType.POWER_INPUT)
        assert len(power_pins) == 2
        assert all(p.electrical_type == PinElectricalType.POWER_INPUT for p in power_pins)

    def test_pin_group_get_pin_numbers(self):
        pins = [
            Pin(number="1", name="A"),
            Pin(number="2", name="B"),
            Pin(number="3", name="C"),
        ]
        group = PinGroup(name="Test", pins=pins)
        assert group.get_pin_numbers() == ["1", "2", "3"]


class TestThermalPad:
    """Tests for ThermalPad model."""

    def test_create_thermal_pad(self):
        pad = ThermalPad(width=3.0, height=3.0)
        assert pad.width == 3.0
        assert pad.height == 3.0
        assert pad.paste_coverage == 0.5
        assert pad.via_count_x == 3
        assert pad.via_count_y == 3

    def test_thermal_pad_area(self):
        pad = ThermalPad(width=3.0, height=4.0)
        assert pad.area == 12.0

    def test_thermal_pad_via_count(self):
        pad = ThermalPad(width=3.0, height=3.0, via_count_x=4, via_count_y=4)
        assert pad.total_via_count == 16

    def test_thermal_pad_invalid_dimensions(self):
        with pytest.raises(ValidationError):
            ThermalPad(width=0, height=3.0)
        with pytest.raises(ValidationError):
            ThermalPad(width=3.0, height=-1.0)


class TestPackageInfo:
    """Tests for PackageInfo model."""

    def test_create_lqfp_package(self):
        pkg = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-48",
            pin_count=48,
            pitch=0.5,
            body_width=7.0,
            body_length=7.0,
            body_height=1.4,
        )
        assert pkg.package_type == PackageType.LQFP
        assert pkg.pin_count == 48
        assert pkg.is_leaded is True
        assert pkg.is_bga is False
        assert pkg.is_leadless is False
        assert pkg.is_quad is True
        assert pkg.pins_per_side == 12

    def test_create_qfn_package_with_thermal_pad(self):
        thermal = ThermalPad(width=3.5, height=3.5)
        pkg = PackageInfo(
            package_type=PackageType.QFN,
            package_name="QFN-32-EP",
            pin_count=33,  # 32 + EP
            pitch=0.5,
            body_width=5.0,
            body_length=5.0,
            body_height=0.9,
            thermal_pad=thermal,
        )
        assert pkg.has_thermal_pad is True
        assert pkg.is_leadless is True
        assert pkg.pins_per_side == 8  # (33-1) / 4

    def test_create_bga_package(self):
        pkg = PackageInfo(
            package_type=PackageType.BGA,
            package_name="BGA-256",
            pin_count=256,
            pitch=0.8,
            body_width=17.0,
            body_length=17.0,
            body_height=1.2,
            ball_diameter=0.45,
            ball_rows=16,
            ball_columns=16,
        )
        assert pkg.is_bga is True
        assert pkg.is_leaded is False
        assert pkg.pins_per_side is None  # Not a quad package

    def test_package_generate_ipc_name(self):
        pkg = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-64",
            pin_count=64,
            pitch=0.5,
            body_width=10.0,
            body_length=10.0,
            body_height=1.4,
        )
        ipc_name = pkg.generate_ipc_name()
        assert "LQFP" in ipc_name
        assert "64" in ipc_name
        assert "10.0x10.0" in ipc_name
        assert "P0.5" in ipc_name

    def test_dual_package_pins_per_row(self):
        pkg = PackageInfo(
            package_type=PackageType.SOIC,
            package_name="SOIC-8",
            pin_count=8,
            pitch=1.27,
            body_width=3.9,
            body_length=4.9,
            body_height=1.75,
        )
        assert pkg.is_dual is True
        assert pkg.pins_per_row == 4


class TestQFPParams:
    """Tests for QFP-specific parameters."""

    def test_create_qfp_params(self):
        params = QFPParams(
            pitch=0.5,
            pin_count=64,
            body_width=10.0,
            body_length=10.0,
            lead_span_x=12.0,
            lead_span_y=12.0,
            lead_width=0.22,
            body_height=1.4,
        )
        assert params.pins_per_side == 16

    def test_qfp_pin_count_must_be_divisible_by_4(self):
        with pytest.raises(ValidationError):
            QFPParams(
                pitch=0.5,
                pin_count=65,  # Not divisible by 4
                body_width=10.0,
                body_length=10.0,
                lead_span_x=12.0,
                lead_span_y=12.0,
                lead_width=0.22,
                body_height=1.4,
            )


class TestQFNParams:
    """Tests for QFN-specific parameters."""

    def test_create_qfn_params(self):
        params = QFNParams(
            pitch=0.5,
            pin_count=32,
            body_width=5.0,
            body_length=5.0,
            terminal_length=0.4,
            terminal_width=0.25,
            thermal_pad=ThermalPad(width=3.5, height=3.5),
        )
        assert params.pins_per_side == 8

    def test_dfn_pin_count_must_be_even(self):
        with pytest.raises(ValidationError):
            QFNParams(
                variant="DFN",
                pitch=0.5,
                pin_count=7,  # Odd number
                body_width=3.0,
                body_length=3.0,
                terminal_length=0.4,
                terminal_width=0.25,
                thermal_pad=ThermalPad(width=1.5, height=1.5),
            )


class TestBGAParams:
    """Tests for BGA-specific parameters."""

    def test_create_bga_params(self):
        params = BGAParams(
            ball_pitch=0.8,
            ball_diameter=0.45,
            rows=16,
            columns=16,
            body_width=17.0,
            body_length=17.0,
            body_height=1.2,
        )
        assert params.max_balls == 256
        assert params.actual_ball_count == 256

    def test_bga_with_depopulated_balls(self):
        params = BGAParams(
            ball_pitch=0.8,
            ball_diameter=0.45,
            rows=4,
            columns=4,
            body_width=5.0,
            body_length=5.0,
            body_height=1.0,
            depopulated_balls=["A1", "D4"],
        )
        assert params.max_balls == 16
        assert params.actual_ball_count == 14

    def test_bga_row_letter(self):
        params = BGAParams(
            ball_pitch=0.8,
            ball_diameter=0.45,
            rows=10,
            columns=10,
            body_width=10.0,
            body_length=10.0,
            body_height=1.0,
        )
        # Default skips I, O, Q, S, X, Z
        assert params.get_row_letter(0) == "A"
        assert params.get_row_letter(1) == "B"
        assert params.get_row_letter(7) == "H"
        assert params.get_row_letter(8) == "J"  # Skips I

    def test_bga_is_ball_populated(self):
        params = BGAParams(
            ball_pitch=0.8,
            ball_diameter=0.45,
            rows=4,
            columns=4,
            body_width=5.0,
            body_length=5.0,
            body_height=1.0,
            depopulated_balls=["A1", "B2"],
        )
        assert params.is_ball_populated("A", 1) is False
        assert params.is_ball_populated("A", 2) is True
        assert params.is_ball_populated("B", 2) is False


class TestComponentInfo:
    """Tests for ComponentInfo model."""

    def test_create_component(self):
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="GND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="IO1", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        comp = ComponentInfo(name="TEST123", pins=pins, manufacturer="ACME")
        assert comp.name == "TEST123"
        assert comp.pin_count == 3
        assert comp.manufacturer == "ACME"

    def test_component_duplicate_pin_numbers_fails(self):
        pins = [
            Pin(number="1", name="VCC"),
            Pin(number="1", name="GND"),  # Duplicate
        ]
        with pytest.raises(ValidationError):
            ComponentInfo(name="TEST", pins=pins)

    def test_component_get_pins_by_electrical_type(self):
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="GND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="IO1", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        comp = ComponentInfo(name="TEST", pins=pins)

        power_pins = comp.get_pins_by_electrical_type(PinElectricalType.POWER_INPUT)
        assert len(power_pins) == 2

    def test_component_get_power_and_ground_pins(self):
        pins = [
            Pin(number="1", name="VCC", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="2", name="GND", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="3", name="VSS", electrical_type=PinElectricalType.POWER_INPUT),
            Pin(number="4", name="IO1", electrical_type=PinElectricalType.BIDIRECTIONAL),
        ]
        comp = ComponentInfo(name="TEST", pins=pins)

        # get_power_pins returns pins where is_power OR is_supply
        # is_power checks electrical_type, is_supply checks name patterns
        power_pins = comp.get_power_pins()
        assert len(power_pins) == 3  # VCC + GND + VSS (all have POWER_INPUT type)

        ground_pins = comp.get_ground_pins()
        assert len(ground_pins) == 2  # GND and VSS (by name pattern)

    def test_component_get_pin_by_number(self):
        pins = [
            Pin(number="1", name="VCC"),
            Pin(number="2", name="GND"),
        ]
        comp = ComponentInfo(name="TEST", pins=pins)

        pin = comp.get_pin_by_number("1")
        assert pin is not None
        assert pin.name == "VCC"

        assert comp.get_pin_by_number("99") is None

    def test_component_get_pin_by_name(self):
        pins = [
            Pin(number="1", name="VCC"),
            Pin(number="2", name="GND"),
        ]
        comp = ComponentInfo(name="TEST", pins=pins)

        pin = comp.get_pin_by_name("vcc")  # Case insensitive
        assert pin is not None
        assert pin.number == "1"

    def test_component_with_package(self):
        pkg = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-32",
            pin_count=32,
            pitch=0.8,
            body_width=7.0,
            body_length=7.0,
            body_height=1.4,
        )
        comp = ComponentInfo(name="TEST", packages=[pkg])
        assert comp.primary_package == pkg
