"""FPGA pinout CSV parser with multi-unit symbol support.

Handles vendor-specific FPGA pinout formats and assigns pins to logical
units based on I/O bank, function, and other criteria.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from kiforge.core.models.component import ComponentInfo
from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle, PinGroupCategory
from kiforge.core.models.pin import Pin, PinGroup


@dataclass
class FPGAUnitConfig:
    """Configuration for an FPGA symbol unit."""

    unit_number: int
    name: str
    category: PinGroupCategory
    description: str = ""


@dataclass
class FPGAPinInfo:
    """Extended pin information for FPGA pins."""

    number: str
    name: str
    bank: str | None = None
    dual_function: str | None = None
    lvds_pair: str | None = None  # Partner pin name for differential pairs
    is_true_of: bool = False  # True = P (positive), False = N (negative)
    highspeed: bool = False
    dqs: str | None = None
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    unit: int = 1


# Standard FPGA unit assignments
FPGA_UNIT_POWER = 1  # Power and ground (common)
FPGA_UNIT_CONFIG = 2  # Configuration pins
FPGA_UNIT_JTAG = 3  # JTAG interface
FPGA_UNIT_BANK_START = 4  # I/O banks start here


def _parse_lvds_field(lvds_str: str) -> tuple[str | None, bool]:
    """Parse LVDS column to extract pair partner and polarity.

    Args:
        lvds_str: LVDS field value (e.g., "True_OF_PL8B", "Comp_OF_PL8A")

    Returns:
        Tuple of (partner_name, is_positive)
    """
    if not lvds_str or lvds_str == "-":
        return None, False

    # True_OF_xxx = this is the positive (P) pin, paired with xxx
    if lvds_str.startswith("True_OF_"):
        return lvds_str[8:], True

    # Comp_OF_xxx = this is the negative (N) pin, paired with xxx
    if lvds_str.startswith("Comp_OF_"):
        return lvds_str[8:], False

    return None, False


def _infer_fpga_electrical_type(name: str, bank: str | None) -> PinElectricalType:
    """Infer electrical type for FPGA pins.

    Args:
        name: Pin name
        bank: Bank identifier

    Returns:
        Inferred electrical type
    """
    name_upper = name.upper()

    # Power pins
    if name_upper.startswith(("VCC", "VBAT")):
        return PinElectricalType.POWER_INPUT

    # Ground pins
    if name_upper.startswith(("VSS", "GND")):
        return PinElectricalType.POWER_INPUT

    # NC pins
    if name_upper in ("NC", "N/C", "-"):
        return PinElectricalType.NOT_CONNECTED

    # Configuration outputs
    if name_upper in ("DONE",):
        return PinElectricalType.OUTPUT

    # Configuration inputs
    if name_upper in ("PROGRAMN", "INITN", "JTAG_EN"):
        return PinElectricalType.INPUT

    # JTAG
    if name_upper in ("TCK", "TMS", "TDI"):
        return PinElectricalType.INPUT
    if name_upper in ("TDO",):
        return PinElectricalType.OUTPUT

    # Clock pins
    if "CLK" in name_upper or "OSC" in name_upper:
        return PinElectricalType.INPUT

    # SerDes/DPHY - differential pairs are typically bidirectional
    if name_upper.startswith(("SD", "DPHY")):
        return PinElectricalType.BIDIRECTIONAL

    # ADC inputs
    if name_upper.startswith("ADC_"):
        return PinElectricalType.INPUT

    # General I/O pins (PL, PR, PT, PB prefixes for Lattice)
    if re.match(r"^P[LRTB]\d+[AB]?$", name_upper):
        return PinElectricalType.BIDIRECTIONAL

    return PinElectricalType.BIDIRECTIONAL


def _classify_fpga_pin(pin_info: FPGAPinInfo) -> tuple[int, PinGroupCategory]:
    """Classify an FPGA pin into a unit and category.

    Args:
        pin_info: Extended pin information

    Returns:
        Tuple of (unit_number, category)
    """
    name = pin_info.name.upper()
    bank = pin_info.bank
    dual_func = (pin_info.dual_function or "").upper()

    # Power pins - always unit 1 (common/shared)
    if name.startswith(("VCC", "VBAT")) or pin_info.electrical_type == PinElectricalType.POWER_INPUT:
        if "GND" in name or "VSS" in name:
            return FPGA_UNIT_POWER, PinGroupCategory.GROUND
        return FPGA_UNIT_POWER, PinGroupCategory.POWER

    # Ground pins - unit 1
    if name.startswith(("VSS", "GND")) or "GND" in name or "VSS" in name:
        return FPGA_UNIT_POWER, PinGroupCategory.GROUND

    # NC pins - unit 1
    if name in ("NC", "N/C", "-") or pin_info.electrical_type == PinElectricalType.NOT_CONNECTED:
        return FPGA_UNIT_POWER, PinGroupCategory.NC

    # JTAG pins - unit 3
    jtag_pins = {"TCK", "TDI", "TDO", "TMS", "TRST", "JTAG_EN"}
    jtag_funcs = {"TCK", "TDI", "TDO", "TMS", "TRST", "SCLK", "SSI", "SSO", "SCSN"}
    if name in jtag_pins or any(f in dual_func for f in jtag_funcs):
        return FPGA_UNIT_JTAG, PinGroupCategory.JTAG

    # Configuration pins - unit 2
    config_pins = {"DONE", "PROGRAMN", "INITN", "CCLK", "CFG", "CRESETB"}
    config_funcs = {"DONE", "PROGRAMN", "INITN", "MCLK", "MISO", "MOSI", "MCSN", "MSDO"}
    if name in config_pins or any(f in dual_func for f in config_funcs):
        return FPGA_UNIT_CONFIG, PinGroupCategory.CONFIG

    # SerDes pins - by bank
    if bank == "80" or name.startswith("SD"):
        return _bank_to_unit("80"), PinGroupCategory.SERDES

    # DPHY pins - by bank (60, 61)
    if bank in ("60", "61") or name.startswith("DPHY"):
        return _bank_to_unit(bank or "60"), PinGroupCategory.DPHY

    # ADC pins - bank 70
    if bank == "70" or name.startswith("ADC"):
        return _bank_to_unit("70"), PinGroupCategory.ADC

    # I/O bank pins
    if bank and bank.isdigit():
        bank_num = int(bank)
        if 0 <= bank_num <= 7:
            return FPGA_UNIT_BANK_START + bank_num, PinGroupCategory.IO_BANK

    # Default to "other" unit
    return FPGA_UNIT_POWER, PinGroupCategory.OTHER


def _bank_to_unit(bank: str) -> int:
    """Map bank identifier to unit number.

    Args:
        bank: Bank identifier string

    Returns:
        Unit number
    """
    bank_mapping = {
        # Standard I/O banks
        "0": FPGA_UNIT_BANK_START + 0,
        "1": FPGA_UNIT_BANK_START + 1,
        "2": FPGA_UNIT_BANK_START + 2,
        "3": FPGA_UNIT_BANK_START + 3,
        "4": FPGA_UNIT_BANK_START + 4,
        "5": FPGA_UNIT_BANK_START + 5,
        "6": FPGA_UNIT_BANK_START + 6,
        "7": FPGA_UNIT_BANK_START + 7,
        # Special function banks
        "60": FPGA_UNIT_BANK_START + 8,   # DPHY0
        "61": FPGA_UNIT_BANK_START + 9,   # DPHY1
        "70": FPGA_UNIT_BANK_START + 10,  # ADC
        "80": FPGA_UNIT_BANK_START + 11,  # SerDes
    }
    return bank_mapping.get(bank, FPGA_UNIT_POWER)


def get_fpga_unit_names() -> dict[int, str]:
    """Get human-readable names for FPGA units.

    Returns:
        Dict mapping unit number to name
    """
    return {
        FPGA_UNIT_POWER: "Power",
        FPGA_UNIT_CONFIG: "Config",
        FPGA_UNIT_JTAG: "JTAG",
        FPGA_UNIT_BANK_START + 0: "Bank 0",
        FPGA_UNIT_BANK_START + 1: "Bank 1",
        FPGA_UNIT_BANK_START + 2: "Bank 2",
        FPGA_UNIT_BANK_START + 3: "Bank 3",
        FPGA_UNIT_BANK_START + 4: "Bank 4",
        FPGA_UNIT_BANK_START + 5: "Bank 5",
        FPGA_UNIT_BANK_START + 6: "Bank 6",
        FPGA_UNIT_BANK_START + 7: "Bank 7",
        FPGA_UNIT_BANK_START + 8: "DPHY0",
        FPGA_UNIT_BANK_START + 9: "DPHY1",
        FPGA_UNIT_BANK_START + 10: "ADC",
        FPGA_UNIT_BANK_START + 11: "SerDes",
    }


def parse_lattice_fpga_csv(
    csv_path: str | Path,
    package_column: str | None = None,
    encoding: str = "utf-8",
) -> tuple[list[Pin], dict[int, list[Pin]]]:
    """Parse a Lattice FPGA pinout CSV file.

    Args:
        csv_path: Path to CSV file
        package_column: Name of package column to use for pin numbers (e.g., "CABGA400")
                       If None, uses first available package column
        encoding: File encoding

    Returns:
        Tuple of (all_pins, pins_by_unit dict)
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    fpga_pins: list[FPGAPinInfo] = []
    package_columns: list[str] = []

    with open(path, encoding=encoding, newline="") as f:
        # Skip comment lines and empty lines at the start
        lines = []
        for line in f:
            stripped = line.strip()
            # Skip lines that are comments or empty
            if stripped.startswith("#") or stripped.startswith('"#') or not stripped or stripped == ",,,,,,,,,,,,,":
                continue
            lines.append(line)

        if not lines:
            raise ValueError("No data rows found in CSV")

        # Parse as CSV
        reader = csv.reader(lines)
        headers = next(reader)

        # Find column indices
        col_indices = {h.strip(): i for i, h in enumerate(headers)}

        # Identify package columns (columns after DQS that aren't empty)
        dqs_idx = col_indices.get("DQS", len(headers))
        for i, h in enumerate(headers):
            if i > dqs_idx and h.strip():
                package_columns.append(h.strip())

        # Select package column for pin numbers
        if package_column:
            if package_column not in col_indices:
                raise ValueError(f"Package column '{package_column}' not found. Available: {package_columns}")
            pkg_col_idx = col_indices[package_column]
        elif package_columns:
            # Use first package column
            pkg_col_idx = col_indices[package_columns[0]]
        else:
            pkg_col_idx = None

        # Parse rows
        for row in reader:
            if not row or len(row) < 2:
                continue

            # Get basic fields
            padn = row[col_indices.get("PADN", 0)].strip()
            func = row[col_indices.get("Pin/Ball Funcion", col_indices.get("Pin/Ball Function", 1))].strip()

            # Skip if no function
            if not func or func == "-":
                continue

            # Get bank
            bank_idx = col_indices.get("BANK", None)
            bank = row[bank_idx].strip() if bank_idx and bank_idx < len(row) else None
            if bank == "-":
                bank = None

            # Get dual function
            dual_idx = col_indices.get("Dual Function", None)
            dual_func = row[dual_idx].strip() if dual_idx and dual_idx < len(row) else None
            if dual_func == "-":
                dual_func = None

            # Get LVDS info
            lvds_idx = col_indices.get("LVDS", None)
            lvds_str = row[lvds_idx].strip() if lvds_idx and lvds_idx < len(row) else ""
            lvds_partner, is_true = _parse_lvds_field(lvds_str)

            # Get highspeed flag
            hs_idx = col_indices.get("HIGHSPEED", None)
            highspeed = False
            if hs_idx and hs_idx < len(row):
                hs_val = row[hs_idx].strip().upper()
                highspeed = hs_val in ("TRUE", "YES", "1")

            # Get DQS
            dqs_idx_val = col_indices.get("DQS", None)
            dqs = row[dqs_idx_val].strip() if dqs_idx_val and dqs_idx_val < len(row) else None
            if dqs == "-" or dqs == "":
                dqs = None

            # Get pin number from package column
            pin_number = None
            if pkg_col_idx and pkg_col_idx < len(row):
                pin_number = row[pkg_col_idx].strip()
                if pin_number == "-" or not pin_number:
                    pin_number = None

            # Skip pins not present in selected package
            if not pin_number:
                continue

            # Infer electrical type
            elec_type = _infer_fpga_electrical_type(func, bank)

            fpga_pin = FPGAPinInfo(
                number=pin_number,
                name=func,
                bank=bank,
                dual_function=dual_func,
                lvds_pair=lvds_partner,
                is_true_of=is_true,
                highspeed=highspeed,
                dqs=dqs,
                electrical_type=elec_type,
            )
            fpga_pins.append(fpga_pin)

    # Classify pins into units
    for fpga_pin in fpga_pins:
        unit, category = _classify_fpga_pin(fpga_pin)
        fpga_pin.unit = unit

    # Convert to Pin objects and group by unit
    pins: list[Pin] = []
    pins_by_unit: dict[int, list[Pin]] = {}

    for fpga_pin in fpga_pins:
        # Determine graphic style
        graphic_style = PinGraphicStyle.LINE
        if fpga_pin.name.upper().startswith(("CLK", "TCK")):
            graphic_style = PinGraphicStyle.CLOCK
        elif fpga_pin.name.upper().endswith("N") and fpga_pin.lvds_pair:
            # Active low for negative differential
            graphic_style = PinGraphicStyle.LINE  # Could use INVERTED if preferred

        # Build alternate names from dual function
        alternates = []
        if fpga_pin.dual_function:
            alternates = [fpga_pin.dual_function]

        pin = Pin(
            number=fpga_pin.number,
            name=fpga_pin.name,
            electrical_type=fpga_pin.electrical_type,
            graphic_style=graphic_style,
            alternate_names=alternates,
            unit=fpga_pin.unit,
        )
        pins.append(pin)

        if fpga_pin.unit not in pins_by_unit:
            pins_by_unit[fpga_pin.unit] = []
        pins_by_unit[fpga_pin.unit].append(pin)

    # Sort pins within each unit for consistent ordering
    for unit_pins in pins_by_unit.values():
        unit_pins.sort(key=lambda p: _pin_sort_key(p))

    return pins, pins_by_unit


def _pin_sort_key(pin: Pin) -> tuple:
    """Generate a sort key for consistent pin ordering.

    Orders by:
    1. Power pins first
    2. Ground pins
    3. Then alphabetically by name
    """
    name = pin.name.upper()

    # Power first
    if name.startswith(("VCC", "VBAT")):
        return (0, name)
    # Ground second
    if name.startswith(("VSS", "GND")):
        return (1, name)
    # NC last
    if name in ("NC", "N/C"):
        return (9, name)

    # Extract numeric suffix for natural sorting
    match = re.match(r"([A-Z_]+)(\d+)([A-Z])?", name)
    if match:
        prefix, num, suffix = match.groups()
        return (2, prefix, int(num), suffix or "")

    return (2, name, 0, "")


def create_fpga_component_from_csv(
    csv_path: str | Path,
    component_name: str,
    manufacturer: str = "",
    description: str = "",
    package_column: str | None = None,
) -> ComponentInfo:
    """Create a ComponentInfo from an FPGA pinout CSV.

    Args:
        csv_path: Path to CSV file
        component_name: Component part number
        manufacturer: Manufacturer name
        description: Component description
        package_column: Package column to use for pin numbers

    Returns:
        ComponentInfo with pins organized into units
    """
    pins, pins_by_unit = parse_lattice_fpga_csv(csv_path, package_column)

    # Count unique units
    num_units = len(pins_by_unit)

    component = ComponentInfo(
        name=component_name,
        manufacturer=manufacturer,
        description=description,
        pins=pins,
        symbol_units=num_units,
    )

    return component
