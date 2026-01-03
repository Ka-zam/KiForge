"""Pin and PinGroup data models."""

from pydantic import BaseModel, Field, field_validator

from kiforge.core.models.enums import (
    PinElectricalType,
    PinGraphicStyle,
    PinGroupCategory,
    PinOrientation,
)


class Pin(BaseModel):
    """A single pin on a component.

    Represents all the information needed to generate both schematic symbol
    pins and footprint pads.
    """

    model_config = {"frozen": True}  # Pins are immutable value objects

    # Identity
    number: str = Field(
        ...,
        min_length=1,
        description="Pin number/designator (e.g., '1', 'A1', 'EP')",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Pin name/function (e.g., 'VCC', 'GPIO0', 'MOSI')",
    )

    # Electrical properties
    electrical_type: PinElectricalType = Field(
        default=PinElectricalType.UNSPECIFIED,
        description="Electrical type for ERC",
    )

    # Visual properties (for symbol)
    graphic_style: PinGraphicStyle = Field(
        default=PinGraphicStyle.LINE,
        description="Visual style in schematic",
    )

    # Alternate functions (for multi-function pins like MCU GPIO)
    alternate_names: list[str] = Field(
        default_factory=list,
        description="Alternate pin functions (e.g., ['TIM1_CH1', 'USART1_TX'])",
    )

    # Physical location hints (for BGA)
    row: str | None = Field(
        default=None,
        description="BGA row letter (e.g., 'A', 'B', 'AA')",
    )
    column: int | None = Field(
        default=None,
        description="BGA column number",
    )

    # Symbol placement
    unit: int = Field(
        default=1,
        ge=1,
        description="Symbol unit number (for multi-unit symbols)",
    )

    # Additional metadata
    description: str | None = Field(
        default=None,
        description="Pin description from datasheet",
    )
    is_hidden: bool = Field(
        default=False,
        description="Whether pin is hidden in symbol (e.g., stacked power pins)",
    )

    @field_validator("number", "name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from pin number and name."""
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def is_power(self) -> bool:
        """Check if this is a power-related pin."""
        return self.electrical_type in (
            PinElectricalType.POWER_INPUT,
            PinElectricalType.POWER_OUTPUT,
        )

    @property
    def is_ground(self) -> bool:
        """Heuristic check for ground pins based on name."""
        name_lower = self.name.lower()
        return any(
            gnd in name_lower for gnd in ["gnd", "vss", "ground", "agnd", "dgnd", "avss", "dvss"]
        )

    @property
    def is_supply(self) -> bool:
        """Heuristic check for power supply pins based on name."""
        name_lower = self.name.lower()
        return any(
            pwr in name_lower
            for pwr in ["vcc", "vdd", "avdd", "dvdd", "vbat", "v+", "vin", "vcore"]
        )

    @property
    def is_nc(self) -> bool:
        """Check if this is a no-connect pin."""
        return self.electrical_type == PinElectricalType.NOT_CONNECTED


class PinGroup(BaseModel):
    """A logical grouping of pins for symbol organization.

    Pin groups help organize pins on the schematic symbol by function
    (e.g., power pins on top, I/O on sides).
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Group name (e.g., 'Power', 'Port A', 'SPI1')",
    )

    category: PinGroupCategory = Field(
        default=PinGroupCategory.OTHER,
        description="Functional category",
    )

    pins: list[Pin] = Field(
        default_factory=list,
        description="Pins in this group",
    )

    # Symbol placement hints
    preferred_side: PinOrientation | None = Field(
        default=None,
        description="Preferred side of symbol for this group",
    )

    unit: int = Field(
        default=1,
        ge=1,
        description="Symbol unit for this group (multi-unit symbols)",
    )

    sort_order: int = Field(
        default=0,
        description="Order for placing groups on symbol (lower = first)",
    )

    @property
    def pin_count(self) -> int:
        """Number of pins in this group."""
        return len(self.pins)

    def get_pins_by_type(self, electrical_type: PinElectricalType) -> list[Pin]:
        """Filter pins by electrical type."""
        return [p for p in self.pins if p.electrical_type == electrical_type]

    def get_pin_numbers(self) -> list[str]:
        """Get list of all pin numbers in this group."""
        return [p.number for p in self.pins]
