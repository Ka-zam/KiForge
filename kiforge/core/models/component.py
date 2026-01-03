"""Master component information model."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from kiforge.core.models.enums import PinElectricalType
from kiforge.core.models.package import PackageInfo
from kiforge.core.models.pin import Pin, PinGroup


class ComponentInfo(BaseModel):
    """Master component information - aggregates all extracted data.

    This is the central data structure that holds all information about
    a component extracted from datasheets and used to generate KiCad
    symbols, footprints, and 3D models.
    """

    # Identity
    name: str = Field(
        ...,
        min_length=1,
        description="Component part number (e.g., 'STM32F407VGT6')",
    )

    manufacturer: str = Field(
        default="",
        description="Manufacturer name",
    )

    description: str = Field(
        default="",
        description="Component description",
    )

    # Classification
    category: str = Field(
        default="",
        description="Component category (e.g., 'MCU', 'Sensor', 'Power')",
    )

    keywords: list[str] = Field(
        default_factory=list,
        description="Search keywords",
    )

    # Datasheet reference
    datasheet_url: str | None = Field(
        default=None,
        description="URL to datasheet",
    )

    datasheet_path: str | None = Field(
        default=None,
        description="Local path to datasheet PDF",
    )

    # Pin information
    pins: list[Pin] = Field(
        default_factory=list,
        description="All component pins",
    )

    pin_groups: list[PinGroup] = Field(
        default_factory=list,
        description="Logical pin groupings for symbol layout",
    )

    # Package information (may support multiple packages)
    packages: list[PackageInfo] = Field(
        default_factory=list,
        description="Available packages for this component",
    )

    # Default/primary package
    primary_package_index: int = Field(
        default=0,
        ge=0,
        description="Index of primary package in packages list",
    )

    # Symbol configuration
    symbol_units: int = Field(
        default=1,
        ge=1,
        description="Number of units in schematic symbol",
    )

    de_morgan_style: bool = Field(
        default=False,
        description="Has alternate De Morgan representation",
    )

    power_symbol: bool = Field(
        default=False,
        description="Is this a power symbol (GND, VCC, etc.)",
    )

    # Additional KiCad properties
    reference_prefix: str = Field(
        default="U",
        min_length=1,
        description="Reference designator prefix (U, R, C, etc.)",
    )

    kicad_properties: dict[str, str] = Field(
        default_factory=dict,
        description="Additional KiCad symbol properties",
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )

    source_document: str | None = Field(
        default=None,
        description="Source document identifier",
    )

    extraction_confidence: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Confidence score of extracted data (1.0 = manual entry)",
    )

    # Validation/review status
    reviewed: bool = Field(
        default=False,
        description="Has been manually reviewed",
    )

    @field_validator("pins")
    @classmethod
    def validate_unique_pin_numbers(cls, pins: list[Pin]) -> list[Pin]:
        """Ensure pin numbers are unique within the component."""
        numbers = [p.number for p in pins]
        if len(numbers) != len(set(numbers)):
            # Find duplicates
            seen = set()
            duplicates = []
            for n in numbers:
                if n in seen:
                    duplicates.append(n)
                seen.add(n)
            raise ValueError(f"Duplicate pin numbers: {set(duplicates)}")
        return pins

    @property
    def pin_count(self) -> int:
        """Total number of pins."""
        return len(self.pins)

    @property
    def primary_package(self) -> PackageInfo | None:
        """Get the primary package, if any."""
        if self.packages and 0 <= self.primary_package_index < len(self.packages):
            return self.packages[self.primary_package_index]
        return None

    def get_pins_by_electrical_type(self, etype: PinElectricalType) -> list[Pin]:
        """Filter pins by electrical type.

        Args:
            etype: Electrical type to filter by

        Returns:
            List of pins with the specified electrical type
        """
        return [p for p in self.pins if p.electrical_type == etype]

    def get_pins_by_unit(self, unit: int) -> list[Pin]:
        """Get pins belonging to a specific symbol unit.

        Args:
            unit: Symbol unit number (1-based)

        Returns:
            List of pins in the specified unit
        """
        return [p for p in self.pins if p.unit == unit]

    def get_pins_by_group(self, group_name: str) -> list[Pin]:
        """Get pins belonging to a named group.

        Args:
            group_name: Name of the pin group

        Returns:
            List of pins in the group, or empty list if not found
        """
        for group in self.pin_groups:
            if group.name == group_name:
                return list(group.pins)
        return []

    def get_power_pins(self) -> list[Pin]:
        """Get all power-related pins (VCC, VDD, etc.)."""
        return [p for p in self.pins if p.is_power or p.is_supply]

    def get_ground_pins(self) -> list[Pin]:
        """Get all ground pins (GND, VSS, etc.)."""
        return [p for p in self.pins if p.is_ground]

    def get_nc_pins(self) -> list[Pin]:
        """Get all no-connect pins."""
        return [p for p in self.pins if p.is_nc]

    def get_pin_by_number(self, number: str) -> Pin | None:
        """Look up a pin by its number.

        Args:
            number: Pin number to find

        Returns:
            Pin if found, None otherwise
        """
        for pin in self.pins:
            if pin.number == number:
                return pin
        return None

    def get_pin_by_name(self, name: str) -> Pin | None:
        """Look up a pin by its name (case-insensitive).

        Args:
            name: Pin name to find

        Returns:
            Pin if found, None otherwise
        """
        name_lower = name.lower()
        for pin in self.pins:
            if pin.name.lower() == name_lower:
                return pin
        return None
