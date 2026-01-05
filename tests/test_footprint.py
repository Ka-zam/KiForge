"""Tests for footprint generator."""

import pytest

from kiforge.core.footprint.qfp import QFPFootprintGenerator, create_qfp_footprint
from kiforge.core.footprint.qfn import QFNFootprintGenerator, create_qfn_footprint
from kiforge.core.footprint.generator import FootprintGenerator, Pad, Line
from kiforge.core.models.enums import PackageType, PadShape, PadType
from kiforge.core.models.package import PackageInfo, ThermalPad
from kiforge.core.models.footprint import FootprintParams, PadDimensions


class TestQFPFootprintGenerator:
    """Tests for QFP footprint generator."""

    def create_lqfp48_params(self) -> FootprintParams:
        """Create standard LQFP-48 parameters for testing."""
        package = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-48",
            pin_count=48,
            pitch=0.5,
            body_width=7.0,
            body_length=7.0,
            body_height=1.4,
            lead_span=9.0,
        )
        pad_size = PadDimensions(width=1.5, height=0.28, corner_ratio=0.25)
        return FootprintParams(
            footprint_name="LQFP-48_7x7mm_P0.5mm",
            package=package,
            pad_size=pad_size,
            pad_center_x=4.25,
            pad_center_y=4.25,
        )

    def test_qfp_pad_count(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        assert len(generator.pads) == 48

    def test_qfp_pad_numbering(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # Check pin numbers are 1-48
        pin_numbers = [p.number for p in generator.pads]
        assert pin_numbers == [str(i) for i in range(1, 49)]

    def test_qfp_pad_positions_left_side(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # First 12 pads should be on left side (negative X)
        left_pads = generator.pads[:12]
        for pad in left_pads:
            assert pad.x < 0, f"Pad {pad.number} should be on left side"

    def test_qfp_pad_positions_bottom_side(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 13-24 should be on bottom (positive Y in PCB coordinates)
        bottom_pads = generator.pads[12:24]
        for pad in bottom_pads:
            assert pad.y > 0, f"Pad {pad.number} should be on bottom side"

    def test_qfp_pad_positions_right_side(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 25-36 should be on right side (positive X)
        right_pads = generator.pads[24:36]
        for pad in right_pads:
            assert pad.x > 0, f"Pad {pad.number} should be on right side"

    def test_qfp_pad_positions_top_side(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 37-48 should be on top (negative Y in PCB coordinates)
        top_pads = generator.pads[36:48]
        for pad in top_pads:
            assert pad.y < 0, f"Pad {pad.number} should be on top side"

    def test_qfp_pad_pitch(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        generator.calculate_pads()

        # Check pitch between adjacent pads on left side
        left_pads = generator.pads[:12]
        for i in range(len(left_pads) - 1):
            dy = left_pads[i + 1].y - left_pads[i].y
            assert abs(dy - 0.5) < 0.001, f"Pitch between pads {i+1} and {i+2} should be 0.5mm"

    def test_qfp_generate_output_format(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        # Check basic structure
        assert content.startswith('(footprint "LQFP-48_7x7mm_P0.5mm"')
        assert "(version 20241229)" in content
        assert '(generator "kiforge")' in content
        assert '(layer "F.Cu")' in content
        assert "(attr smd)" in content

    def test_qfp_generate_contains_pads(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        # Check for pad definitions
        assert '(pad "1" smd roundrect' in content
        assert '(pad "48" smd roundrect' in content

    def test_qfp_generate_contains_silkscreen(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert '(layer "F.SilkS")' in content

    def test_qfp_generate_contains_courtyard(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert '(layer "F.CrtYd")' in content

    def test_qfp_generate_contains_fab_layer(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert '(layer "F.Fab")' in content

    def test_qfp_generate_contains_reference(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert '(fp_text reference "REF**"' in content

    def test_qfp_generate_contains_value(self):
        params = self.create_lqfp48_params()
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert f'(fp_text value "{params.footprint_name}"' in content


class TestCreateQFPFootprint:
    """Tests for the create_qfp_footprint convenience function."""

    def test_create_lqfp_32(self):
        content = create_qfp_footprint(
            pins=32,
            pitch=0.8,
            body_width=7.0,
            body_length=7.0,
            lead_span=9.0,
            variant="LQFP",
        )

        assert '(footprint "LQFP-32_7.0x7.0mm_P0.8mm"' in content
        assert '(pad "1" smd' in content
        assert '(pad "32" smd' in content

    def test_create_tqfp_64(self):
        content = create_qfp_footprint(
            pins=64,
            pitch=0.5,
            body_width=10.0,
            body_length=10.0,
            lead_span=12.0,
            body_height=1.0,
            variant="TQFP",
        )

        assert "TQFP-64" in content
        assert '(pad "64" smd' in content

    def test_create_qfp_invalid_pin_count(self):
        with pytest.raises(ValueError, match="divisible by 4"):
            create_qfp_footprint(
                pins=30,  # Not divisible by 4
                pitch=0.5,
                body_width=7.0,
                body_length=7.0,
                lead_span=9.0,
            )

    def test_create_qfp_with_3d_model(self):
        package = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-32",
            pin_count=32,
            pitch=0.8,
            body_width=7.0,
            body_length=7.0,
            body_height=1.4,
            lead_span=9.0,
        )
        pad_size = PadDimensions(width=1.5, height=0.4)
        params = FootprintParams(
            footprint_name="LQFP-32_7x7mm_P0.8mm",
            package=package,
            pad_size=pad_size,
            pad_center_x=4.5,
            pad_center_y=4.5,
            model_3d_path="${KICAD8_3DMODEL_DIR}/Package_QFP.3dshapes/LQFP-32_7x7mm_P0.8mm.step",
        )
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        assert "(model " in content
        assert "LQFP-32_7x7mm_P0.8mm.step" in content


class TestThermalPadGeneration:
    """Tests for thermal pad generation."""

    def test_footprint_with_thermal_pad(self):
        thermal = ThermalPad(
            width=3.5,
            height=3.5,
            via_count_x=3,
            via_count_y=3,
            via_drill=0.3,
            via_pad_diameter=0.5,
            pin_number="EP",
        )
        package = PackageInfo(
            package_type=PackageType.LQFP,
            package_name="LQFP-32-EP",
            pin_count=33,
            pitch=0.8,
            body_width=7.0,
            body_length=7.0,
            body_height=1.4,
            lead_span=9.0,
            thermal_pad=thermal,
        )
        pad_size = PadDimensions(width=1.5, height=0.4)
        params = FootprintParams(
            footprint_name="LQFP-32-1EP_7x7mm_P0.8mm",
            package=package,
            pad_size=pad_size,
            pad_center_x=4.5,
            pad_center_y=4.5,
        )
        generator = QFPFootprintGenerator(params)
        content = generator.generate()

        # Check for exposed pad
        assert '(pad "EP" smd rect' in content
        # Check for thermal vias (9 vias = 3x3)
        assert content.count("pad_prop_heatsink") == 9


class TestPadDataclass:
    """Tests for Pad dataclass."""

    def test_create_smd_pad(self):
        pad = Pad(
            number="1",
            pad_type=PadType.SMD,
            shape=PadShape.ROUNDRECT,
            x=1.0,
            y=2.0,
            width=0.5,
            height=1.0,
        )
        assert pad.number == "1"
        assert pad.pad_type == PadType.SMD
        assert pad.x == 1.0
        assert pad.y == 2.0

    def test_create_thru_hole_pad(self):
        pad = Pad(
            number="1",
            pad_type=PadType.THRU_HOLE,
            shape=PadShape.CIRCLE,
            x=0.0,
            y=0.0,
            width=1.7,
            height=1.7,
            drill=1.0,
            layers=["*.Cu", "*.Mask"],
        )
        assert pad.drill == 1.0
        assert "*.Cu" in pad.layers


class TestLineDataclass:
    """Tests for Line dataclass."""

    def test_create_line(self):
        line = Line(x1=0, y1=0, x2=10, y2=10, layer="F.SilkS", width=0.12)
        assert line.x1 == 0
        assert line.x2 == 10
        assert line.layer == "F.SilkS"
        assert line.width == 0.12


class TestQFNFootprintGenerator:
    """Tests for QFN footprint generator."""

    def create_qfn32_params(self) -> FootprintParams:
        """Create standard QFN-32 parameters for testing."""
        thermal = ThermalPad(
            width=3.5,
            height=3.5,
            via_count_x=3,
            via_count_y=3,
            via_drill=0.3,
            via_pad_diameter=0.5,
            pin_number="EP",
        )
        package = PackageInfo(
            package_type=PackageType.QFN,
            package_name="QFN-32-EP",
            pin_count=33,  # 32 + thermal pad
            pitch=0.5,
            body_width=5.0,
            body_length=5.0,
            body_height=0.9,
            thermal_pad=thermal,
        )
        pad_size = PadDimensions(
            width=0.7,
            height=0.25,
            shape=PadShape.ROUNDRECT,
            corner_ratio=0.25,
        )
        return FootprintParams(
            footprint_name="QFN-32-1EP_5x5mm_P0.5mm",
            package=package,
            pad_size=pad_size,
            pad_center_x=2.35,
            pad_center_y=2.35,
        )

    def test_qfn_pad_count(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # 32 signal pads (thermal pad added separately)
        assert len(generator.pads) == 32

    def test_qfn_pad_numbering(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        pin_numbers = [p.number for p in generator.pads]
        assert pin_numbers == [str(i) for i in range(1, 33)]

    def test_qfn_pad_positions_left_side(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # First 8 pads should be on left side (negative X)
        left_pads = generator.pads[:8]
        for pad in left_pads:
            assert pad.x < 0, f"Pad {pad.number} should be on left side"

    def test_qfn_pad_positions_bottom_side(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 9-16 should be on bottom (positive Y)
        bottom_pads = generator.pads[8:16]
        for pad in bottom_pads:
            assert pad.y > 0, f"Pad {pad.number} should be on bottom side"

    def test_qfn_pad_positions_right_side(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 17-24 should be on right side (positive X)
        right_pads = generator.pads[16:24]
        for pad in right_pads:
            assert pad.x > 0, f"Pad {pad.number} should be on right side"

    def test_qfn_pad_positions_top_side(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 25-32 should be on top (negative Y)
        top_pads = generator.pads[24:32]
        for pad in top_pads:
            assert pad.y < 0, f"Pad {pad.number} should be on top side"

    def test_qfn_pad_pitch(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # Check pitch between adjacent pads on left side
        left_pads = generator.pads[:8]
        for i in range(len(left_pads) - 1):
            dy = left_pads[i + 1].y - left_pads[i].y
            assert abs(dy - 0.5) < 0.001, f"Pitch between pads {i+1} and {i+2} should be 0.5mm"

    def test_qfn_generate_output_format(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        content = generator.generate()

        assert content.startswith('(footprint "QFN-32-1EP_5x5mm_P0.5mm"')
        assert "(version 20241229)" in content
        assert '(generator "kiforge")' in content
        assert '(layer "F.Cu")' in content
        assert "(attr smd)" in content

    def test_qfn_generate_contains_pads(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        content = generator.generate()

        assert '(pad "1" smd roundrect' in content
        assert '(pad "32" smd roundrect' in content

    def test_qfn_generate_contains_thermal_pad(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        content = generator.generate()

        assert '(pad "EP" smd rect' in content

    def test_qfn_generate_contains_thermal_vias(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        content = generator.generate()

        # 9 thermal vias (3x3 grid)
        assert content.count("pad_prop_heatsink") == 9

    def test_qfn_generate_contains_silkscreen(self):
        params = self.create_qfn32_params()
        generator = QFNFootprintGenerator(params)
        content = generator.generate()

        assert '(layer "F.SilkS")' in content


class TestDFNFootprintGenerator:
    """Tests for DFN (2-sided) footprint generator."""

    def create_dfn8_params(self) -> FootprintParams:
        """Create standard DFN-8 parameters for testing."""
        thermal = ThermalPad(
            width=1.5,
            height=1.5,
            via_count_x=2,
            via_count_y=2,
            via_drill=0.3,
            via_pad_diameter=0.5,
            pin_number="EP",
        )
        package = PackageInfo(
            package_type=PackageType.DFN,
            package_name="DFN-8-EP",
            pin_count=9,  # 8 + thermal pad
            pitch=0.5,
            body_width=3.0,
            body_length=3.0,
            body_height=0.75,
            thermal_pad=thermal,
        )
        pad_size = PadDimensions(
            width=0.6,
            height=0.25,
            shape=PadShape.ROUNDRECT,
            corner_ratio=0.25,
        )
        return FootprintParams(
            footprint_name="DFN-8-1EP_3x3mm_P0.5mm",
            package=package,
            pad_size=pad_size,
            pad_center_x=1.35,
            pad_center_y=1.35,
        )

    def test_dfn_pad_count(self):
        params = self.create_dfn8_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # 8 signal pads
        assert len(generator.pads) == 8

    def test_dfn_pad_positions_left_side(self):
        params = self.create_dfn8_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # First 4 pads should be on left side
        left_pads = generator.pads[:4]
        for pad in left_pads:
            assert pad.x < 0, f"Pad {pad.number} should be on left side"

    def test_dfn_pad_positions_right_side(self):
        params = self.create_dfn8_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # Pads 5-8 should be on right side
        right_pads = generator.pads[4:8]
        for pad in right_pads:
            assert pad.x > 0, f"Pad {pad.number} should be on right side"

    def test_dfn_no_top_bottom_pads(self):
        params = self.create_dfn8_params()
        generator = QFNFootprintGenerator(params)
        generator.calculate_pads()

        # All pads should be on left or right (no Y-only positions)
        for pad in generator.pads:
            assert pad.x != 0, f"Pad {pad.number} should not be at center X"


class TestCreateQFNFootprint:
    """Tests for the create_qfn_footprint convenience function."""

    def test_create_qfn32(self):
        content = create_qfn_footprint(
            pins=32,
            pitch=0.5,
            body_width=5.0,
            body_length=5.0,
            thermal_pad_size=3.5,
            variant="QFN",
        )

        assert "QFN-32" in content
        assert '(pad "1" smd' in content
        assert '(pad "32" smd' in content
        assert '(pad "EP" smd' in content

    def test_create_qfn_square_body(self):
        content = create_qfn_footprint(
            pins=24,
            pitch=0.5,
            body_width=4.0,
        )

        # Default body_length should equal body_width
        assert "4.0x4.0" in content or "4x4" in content

    def test_create_dfn8(self):
        content = create_qfn_footprint(
            pins=8,
            pitch=0.5,
            body_width=3.0,
            body_length=3.0,
            thermal_pad_size=1.5,
            variant="DFN",
        )

        assert "DFN-8" in content
        assert '(pad "8" smd' in content

    def test_create_qfn_invalid_pin_count_qfn(self):
        with pytest.raises(ValueError, match="divisible by 4"):
            create_qfn_footprint(
                pins=30,  # Not divisible by 4
                pitch=0.5,
                body_width=5.0,
                variant="QFN",
            )

    def test_create_qfn_invalid_pin_count_dfn(self):
        with pytest.raises(ValueError, match="divisible by 2"):
            create_qfn_footprint(
                pins=7,  # Odd number
                pitch=0.5,
                body_width=3.0,
                variant="DFN",
            )

    def test_create_vqfn(self):
        content = create_qfn_footprint(
            pins=16,
            pitch=0.5,
            body_width=3.0,
            variant="VQFN",
        )

        assert "VQFN-16" in content

    def test_create_wqfn(self):
        content = create_qfn_footprint(
            pins=20,
            pitch=0.5,
            body_width=4.0,
            variant="WQFN",
        )

        assert "WQFN-20" in content

    def test_create_qfn_default_thermal_pad(self):
        content = create_qfn_footprint(
            pins=32,
            pitch=0.5,
            body_width=5.0,
        )

        # Should have thermal pad by default (60% of body)
        assert '(pad "EP"' in content

    def test_create_qfn_with_rectangular_body(self):
        content = create_qfn_footprint(
            pins=24,
            pitch=0.5,
            body_width=4.0,
            body_length=5.0,
        )

        assert "4.0x5.0" in content or "4x5" in content
