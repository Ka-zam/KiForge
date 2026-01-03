"""Footprint generation parameters."""

from typing import Literal

from pydantic import BaseModel, Field

from kiforge.core.models.enums import PadShape, PadType
from kiforge.core.models.package import PackageInfo, ThermalPad


class PadDimensions(BaseModel):
    """Dimensions for a single pad type.

    Used to specify the size and shape of SMD or through-hole pads.
    """

    model_config = {"frozen": True}

    width: float = Field(..., gt=0, description="Pad width in mm")
    height: float = Field(..., gt=0, description="Pad height in mm")
    shape: PadShape = Field(
        default=PadShape.ROUNDRECT,
        description="Pad shape",
    )
    corner_ratio: float = Field(
        default=0.25,
        ge=0,
        le=0.5,
        description="Corner radius ratio for roundrect (0-0.5)",
    )


class FootprintParams(BaseModel):
    """All parameters needed to generate a KiCad footprint.

    This model contains everything required to generate a complete
    .kicad_mod footprint file including pads, silkscreen, courtyard,
    and 3D model reference.
    """

    # Naming
    footprint_name: str = Field(
        ...,
        min_length=1,
        description="Footprint name (e.g., 'LQFP-64_10x10mm_P0.5mm')",
    )

    library_name: str = Field(
        default="KiForge",
        description="Target KiCad library name",
    )

    description: str = Field(
        default="",
        description="Footprint description",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Search tags for the footprint",
    )

    # Reference package info
    package: PackageInfo = Field(
        ...,
        description="Package dimensions and type",
    )

    # Pad configuration
    pad_size: PadDimensions = Field(
        ...,
        description="Standard pad dimensions",
    )

    pad_type: PadType = Field(
        default=PadType.SMD,
        description="Pad type (SMD, THT, etc.)",
    )

    # Layout parameters - distance from origin to pad center
    pad_center_x: float = Field(
        ...,
        description="X distance from origin to outer pad center (for left/right pads)",
    )
    pad_center_y: float = Field(
        ...,
        description="Y distance from origin to outer pad center (for top/bottom pads)",
    )

    # Courtyard (assembly boundary)
    courtyard_margin: float = Field(
        default=0.25,
        gt=0,
        description="Courtyard margin beyond pads in mm",
    )
    courtyard_line_width: float = Field(
        default=0.05,
        gt=0,
        description="Courtyard line width in mm",
    )

    # Silkscreen
    silkscreen_margin: float = Field(
        default=0.15,
        gt=0,
        description="Silkscreen offset from pads in mm",
    )
    silkscreen_line_width: float = Field(
        default=0.12,
        gt=0,
        description="Silkscreen line width in mm",
    )

    # Fab layer
    fab_line_width: float = Field(
        default=0.1,
        gt=0,
        description="Fabrication layer line width in mm",
    )

    # Pin 1 indicator
    pin1_marker: Literal["chamfer", "dot", "triangle"] = Field(
        default="chamfer",
        description="Pin 1 indicator style on silkscreen",
    )

    # Thermal pad override (uses package thermal_pad if not specified)
    thermal_pad_override: ThermalPad | None = Field(
        default=None,
        description="Override package thermal pad parameters",
    )

    # Solder paste
    paste_margin: float = Field(
        default=0.0,
        description="Solder paste margin (negative = inset from pad)",
    )
    paste_ratio: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Solder paste ratio (1.0 = 100% coverage)",
    )

    # Solder mask
    mask_margin: float = Field(
        default=0.05,
        ge=0,
        description="Solder mask expansion in mm",
    )

    # 3D model reference
    model_3d_path: str | None = Field(
        default=None,
        description="Path to 3D model file (relative or using ${VAR})",
    )
    model_3d_offset: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0),
        description="3D model offset (x, y, z) in mm",
    )
    model_3d_rotation: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0),
        description="3D model rotation (x, y, z) in degrees",
    )
    model_3d_scale: tuple[float, float, float] = Field(
        default=(1.0, 1.0, 1.0),
        description="3D model scale factors",
    )

    # IPC density level
    density_level: Literal["L", "N", "M"] = Field(
        default="N",
        description="IPC-7351 density: L=Least, N=Nominal, M=Most",
    )

    @property
    def has_thermal_pad(self) -> bool:
        """Check if footprint has a thermal pad."""
        return self.thermal_pad_override is not None or self.package.has_thermal_pad

    @property
    def thermal_pad(self) -> ThermalPad | None:
        """Get effective thermal pad (override or package default)."""
        return self.thermal_pad_override or self.package.thermal_pad

    @property
    def full_name(self) -> str:
        """Full footprint name with library prefix."""
        return f"{self.library_name}:{self.footprint_name}"
