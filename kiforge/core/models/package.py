"""Package information and dimension models."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from kiforge.core.models.enums import BGABallPattern, PackageType


class ThermalPad(BaseModel):
    """Exposed thermal pad (EP) configuration.

    Many modern packages (QFN, some QFP) have an exposed metal pad on the
    bottom for heat dissipation. This pad typically connects to ground
    and may require thermal vias.
    """

    # Dimensions
    width: float = Field(..., gt=0, description="Pad width in mm")
    height: float = Field(..., gt=0, description="Pad height in mm")

    # PCB landing adjustments
    paste_coverage: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Solder paste coverage ratio (0.5-0.8 recommended)",
    )

    # Thermal vias
    via_count_x: int = Field(
        default=3,
        ge=0,
        description="Number of thermal vias in X direction",
    )
    via_count_y: int = Field(
        default=3,
        ge=0,
        description="Number of thermal vias in Y direction",
    )
    via_drill: float = Field(
        default=0.3,
        gt=0,
        description="Thermal via drill diameter in mm",
    )
    via_pad_diameter: float = Field(
        default=0.5,
        gt=0,
        description="Thermal via pad diameter in mm",
    )

    # Pad shape
    corner_radius: float = Field(
        default=0.0,
        ge=0,
        description="Corner radius for rounded rectangle (0 = sharp corners)",
    )

    # Electrical connection
    pin_number: str = Field(
        default="EP",
        description="Pin number for thermal pad connection",
    )

    @property
    def area(self) -> float:
        """Thermal pad area in mm^2."""
        return self.width * self.height

    @property
    def total_via_count(self) -> int:
        """Total number of thermal vias."""
        return self.via_count_x * self.via_count_y


class PackageInfo(BaseModel):
    """Package type and physical dimensions.

    Contains all the physical characteristics of an IC package needed
    to generate footprints and 3D models.
    """

    # Package identification
    package_type: PackageType = Field(
        ...,
        description="Package family",
    )

    package_name: str = Field(
        ...,
        min_length=1,
        description="Full package name (e.g., 'LQFP-64', 'QFN-32-EP')",
    )

    # Lead configuration
    pin_count: int = Field(
        ...,
        gt=0,
        description="Total pin count including thermal pad",
    )

    pitch: float = Field(
        ...,
        gt=0,
        description="Lead pitch in mm (0.4, 0.5, 0.65, 0.8, 1.0 typical)",
    )

    # Body dimensions
    body_width: float = Field(
        ...,
        gt=0,
        description="Package body width in mm (X dimension)",
    )
    body_length: float = Field(
        ...,
        gt=0,
        description="Package body length in mm (Y dimension)",
    )
    body_height: float = Field(
        ...,
        gt=0,
        description="Package body height/thickness in mm (Z dimension)",
    )

    # Lead dimensions (for leaded packages: QFP, SOIC, etc.)
    lead_width: float | None = Field(
        default=None,
        gt=0,
        description="Lead width in mm",
    )
    lead_length: float | None = Field(
        default=None,
        gt=0,
        description="Lead length (foot) in mm",
    )
    lead_span: float | None = Field(
        default=None,
        gt=0,
        description="Lead span (tip-to-tip) in mm",
    )

    # Thermal pad
    thermal_pad: ThermalPad | None = Field(
        default=None,
        description="Exposed thermal pad configuration",
    )

    # BGA-specific
    ball_diameter: float | None = Field(
        default=None,
        gt=0,
        description="BGA solder ball diameter in mm",
    )
    ball_pattern: BGABallPattern | None = Field(
        default=None,
        description="BGA ball array pattern",
    )
    ball_rows: int | None = Field(
        default=None,
        gt=0,
        description="Number of ball rows",
    )
    ball_columns: int | None = Field(
        default=None,
        gt=0,
        description="Number of ball columns",
    )
    depopulated_positions: list[str] | None = Field(
        default=None,
        description="List of depopulated ball positions (e.g., ['A1', 'A2'])",
    )

    # IPC-7351 naming
    ipc_name: str | None = Field(
        default=None,
        description="IPC-7351 compliant name",
    )

    # Manufacturer-specific
    manufacturer_code: str | None = Field(
        default=None,
        description="Manufacturer's package code",
    )

    @property
    def has_thermal_pad(self) -> bool:
        """Check if package has an exposed thermal pad."""
        return self.thermal_pad is not None

    @property
    def is_leaded(self) -> bool:
        """Check if package has external leads (vs leadless/BGA)."""
        return self.package_type in (
            PackageType.QFP,
            PackageType.LQFP,
            PackageType.TQFP,
            PackageType.VQFP,
            PackageType.SOIC,
            PackageType.SOP,
            PackageType.SSOP,
            PackageType.TSSOP,
            PackageType.MSOP,
            PackageType.DIP,
        )

    @property
    def is_bga(self) -> bool:
        """Check if package is a BGA variant."""
        return self.package_type in (
            PackageType.BGA,
            PackageType.FBGA,
            PackageType.TFBGA,
            PackageType.UFBGA,
            PackageType.WLCSP,
            PackageType.DSBGA,
        )

    @property
    def is_leadless(self) -> bool:
        """Check if package is leadless (QFN/DFN)."""
        return self.package_type in (
            PackageType.QFN,
            PackageType.VQFN,
            PackageType.WQFN,
            PackageType.DFN,
        )

    @property
    def is_quad(self) -> bool:
        """Check if package has pins on 4 sides."""
        return self.package_type in (
            PackageType.QFP,
            PackageType.LQFP,
            PackageType.TQFP,
            PackageType.VQFP,
            PackageType.QFN,
            PackageType.VQFN,
            PackageType.WQFN,
        )

    @property
    def is_dual(self) -> bool:
        """Check if package has pins on 2 sides."""
        return self.package_type in (
            PackageType.DFN,
            PackageType.SOIC,
            PackageType.SOP,
            PackageType.SSOP,
            PackageType.TSSOP,
            PackageType.MSOP,
            PackageType.DIP,
        )

    @property
    def pins_per_side(self) -> int | None:
        """Calculate pins per side for quad packages."""
        if not self.is_quad:
            return None
        # Subtract thermal pad if present
        effective_pins = self.pin_count
        if self.has_thermal_pad:
            effective_pins -= 1
        return effective_pins // 4

    @property
    def pins_per_row(self) -> int | None:
        """Calculate pins per row for dual packages."""
        if not self.is_dual:
            return None
        # Subtract thermal pad if present
        effective_pins = self.pin_count
        if self.has_thermal_pad:
            effective_pins -= 1
        return effective_pins // 2

    def generate_ipc_name(self) -> str:
        """Generate IPC-7351B compliant footprint name."""
        parts = [self.package_type.value]

        # Pin count
        pin_str = str(self.pin_count)
        if self.has_thermal_pad:
            pin_str += "-1EP"
        parts.append(f"-{pin_str}")

        # Body size
        parts.append(f"_{self.body_width}x{self.body_length}mm")

        # Pitch
        parts.append(f"_P{self.pitch}mm")

        # Thermal pad size
        if self.has_thermal_pad and self.thermal_pad:
            parts.append(f"_EP{self.thermal_pad.width}x{self.thermal_pad.height}mm")

        return "".join(parts)


class QFPParams(BaseModel):
    """QFP/LQFP/TQFP specific parameters for footprint generation."""

    variant: Literal["QFP", "LQFP", "TQFP", "VQFP"] = Field(
        default="LQFP",
        description="QFP variant",
    )

    pitch: float = Field(
        ...,
        gt=0,
        description="Lead pitch (0.4, 0.5, 0.65, 0.8, 1.0 mm)",
    )

    pin_count: int = Field(
        ...,
        gt=0,
        description="Total pin count (32, 44, 48, 64, 80, 100, 144, 176, 208, 256)",
    )

    # Body size
    body_width: float = Field(..., gt=0, description="Body width in mm")
    body_length: float = Field(..., gt=0, description="Body length in mm")

    # Lead span (tip to tip across package)
    lead_span_x: float = Field(..., gt=0, description="Lead span in X direction")
    lead_span_y: float = Field(..., gt=0, description="Lead span in Y direction")

    # Lead dimensions
    lead_length: float = Field(default=0.6, gt=0, description="Lead foot length in mm")
    lead_width: float = Field(..., gt=0, description="Lead width in mm")

    # Height (determines QFP variant)
    body_height: float = Field(
        ...,
        gt=0,
        description="Body height (1.0mm=TQFP, 1.4mm=LQFP, >1.4mm=QFP)",
    )

    # Optional exposed pad
    thermal_pad: ThermalPad | None = Field(
        default=None,
        description="Optional exposed thermal pad",
    )

    @field_validator("pin_count")
    @classmethod
    def validate_quad_pin_count(cls, v: int) -> int:
        """Validate that pin count is divisible by 4."""
        if v % 4 != 0:
            raise ValueError("QFP pin count must be divisible by 4")
        return v

    @property
    def pins_per_side(self) -> int:
        """Pins on each side of the package."""
        return self.pin_count // 4


class QFNParams(BaseModel):
    """QFN/DFN specific parameters for footprint generation."""

    variant: Literal["QFN", "DFN", "VQFN", "WQFN"] = Field(
        default="QFN",
        description="QFN variant",
    )

    pitch: float = Field(
        ...,
        gt=0,
        description="Terminal pitch (0.4, 0.5, 0.65, 0.8, 1.0 mm)",
    )

    pin_count: int = Field(
        ...,
        gt=0,
        description="Total pin count (excluding thermal pad)",
    )

    # Body dimensions
    body_width: float = Field(..., gt=0, description="Body width in mm")
    body_length: float = Field(..., gt=0, description="Body length in mm")
    body_height: float = Field(default=0.9, gt=0, description="Body height in mm")

    # Terminal dimensions
    terminal_length: float = Field(..., gt=0, description="Terminal length in mm")
    terminal_width: float = Field(..., gt=0, description="Terminal width in mm")

    # Exposed thermal pad (typically required for QFN)
    thermal_pad: ThermalPad = Field(
        ...,
        description="Exposed die pad dimensions",
    )

    # Pull-back (distance from body edge to terminal edge)
    pullback: float = Field(
        default=0.0,
        ge=0,
        description="Terminal pullback from package edge",
    )

    @model_validator(mode="after")
    def validate_pin_count_for_variant(self) -> "QFNParams":
        """Validate pin count is appropriate for the variant."""
        if self.variant in ("QFN", "VQFN", "WQFN") and self.pin_count % 4 != 0:
            raise ValueError("QFN pin count must be divisible by 4")
        if self.variant == "DFN" and self.pin_count % 2 != 0:
            raise ValueError("DFN pin count must be divisible by 2")
        return self

    @property
    def pins_per_side(self) -> int:
        """Pins on each side (for QFN)."""
        if self.variant == "DFN":
            return self.pin_count // 2
        return self.pin_count // 4


class BGAParams(BaseModel):
    """BGA specific parameters for footprint generation."""

    variant: Literal["BGA", "FBGA", "TFBGA", "UFBGA", "WLCSP", "DSBGA"] = Field(
        default="BGA",
        description="BGA variant",
    )

    # Ball array configuration
    ball_pitch: float = Field(
        ...,
        gt=0,
        description="Ball pitch (0.4, 0.5, 0.65, 0.8, 1.0, 1.27 mm)",
    )

    ball_diameter: float = Field(
        ...,
        gt=0,
        description="Solder ball diameter (typically 60% of pitch)",
    )

    # Array dimensions
    rows: int = Field(..., gt=0, description="Number of rows (A, B, C...)")
    columns: int = Field(..., gt=0, description="Number of columns (1, 2, 3...)")

    # Body dimensions
    body_width: float = Field(..., gt=0, description="Body width in mm")
    body_length: float = Field(..., gt=0, description="Body length in mm")
    body_height: float = Field(..., gt=0, description="Body height in mm")

    # Ball pattern
    pattern: BGABallPattern = Field(
        default=BGABallPattern.FULL_MATRIX,
        description="Ball array pattern",
    )

    # Depopulated positions (for non-full patterns)
    depopulated_balls: list[str] = Field(
        default_factory=list,
        description="List of depopulated positions (e.g., ['A1', 'P16'])",
    )

    # Row naming (for packages with >26 rows)
    skip_letters: list[str] = Field(
        default_factory=lambda: ["I", "O", "Q", "S", "X", "Z"],
        description="Letters to skip in row naming (avoid confusion with numbers)",
    )

    @property
    def max_balls(self) -> int:
        """Maximum possible balls in full array."""
        return self.rows * self.columns

    @property
    def actual_ball_count(self) -> int:
        """Actual ball count accounting for depopulation."""
        return self.max_balls - len(self.depopulated_balls)

    def get_row_letter(self, row_index: int) -> str:
        """Convert row index to letter, skipping specified letters.

        Args:
            row_index: 0-based row index

        Returns:
            Row letter (e.g., 'A', 'B', 'C', skipping 'I', 'O', etc.)
        """
        letters = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in self.skip_letters]
        if row_index < len(letters):
            return letters[row_index]
        # For >26 rows, use AA, AB, etc.
        first = row_index // len(letters) - 1
        second = row_index % len(letters)
        return letters[first] + letters[second]

    def is_ball_populated(self, row: str, column: int) -> bool:
        """Check if a ball position is populated.

        Args:
            row: Row letter (e.g., 'A', 'B')
            column: Column number (1-based)

        Returns:
            True if the position should have a ball
        """
        position = f"{row}{column}"
        return position not in self.depopulated_balls
