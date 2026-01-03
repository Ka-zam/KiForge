"""CSV pinout file parser."""

import csv
from pathlib import Path

from kiforge.core.models.component import ComponentInfo
from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle
from kiforge.core.models.pin import Pin
from kiforge.core.parser.inference import (
    infer_pin_electrical_type,
    infer_pin_graphic_style,
)


# Common column name variations
PIN_NUMBER_COLUMNS = ["pin", "pin_number", "pin_num", "number", "num", "#", "pin#", "no", "no."]
PIN_NAME_COLUMNS = ["name", "pin_name", "signal", "function", "symbol", "label"]
PIN_TYPE_COLUMNS = ["type", "pin_type", "electrical_type", "io", "i/o", "direction", "dir"]
PIN_DESC_COLUMNS = ["description", "desc", "comment", "notes", "function_description"]
PIN_ALT_COLUMNS = ["alternate", "alt", "alt_function", "alternate_function", "alt_functions"]

# Pin type mappings from common datasheet conventions
TYPE_MAPPINGS = {
    # Input types
    "i": PinElectricalType.INPUT,
    "in": PinElectricalType.INPUT,
    "input": PinElectricalType.INPUT,
    # Output types
    "o": PinElectricalType.OUTPUT,
    "out": PinElectricalType.OUTPUT,
    "output": PinElectricalType.OUTPUT,
    # Bidirectional
    "io": PinElectricalType.BIDIRECTIONAL,
    "i/o": PinElectricalType.BIDIRECTIONAL,
    "inout": PinElectricalType.BIDIRECTIONAL,
    "bidir": PinElectricalType.BIDIRECTIONAL,
    "bidirectional": PinElectricalType.BIDIRECTIONAL,
    # Power
    "p": PinElectricalType.POWER_INPUT,
    "pwr": PinElectricalType.POWER_INPUT,
    "power": PinElectricalType.POWER_INPUT,
    "s": PinElectricalType.POWER_INPUT,  # Supply
    "supply": PinElectricalType.POWER_INPUT,
    # Ground
    "g": PinElectricalType.POWER_INPUT,
    "gnd": PinElectricalType.POWER_INPUT,
    "ground": PinElectricalType.POWER_INPUT,
    # Passive
    "passive": PinElectricalType.PASSIVE,
    "analog": PinElectricalType.PASSIVE,
    # Tristate
    "tristate": PinElectricalType.TRISTATE,
    "tri": PinElectricalType.TRISTATE,
    "t": PinElectricalType.TRISTATE,
    "hi-z": PinElectricalType.TRISTATE,
    # Open drain/collector
    "od": PinElectricalType.OPEN_COLLECTOR,
    "open_drain": PinElectricalType.OPEN_COLLECTOR,
    "open-drain": PinElectricalType.OPEN_COLLECTOR,
    "oc": PinElectricalType.OPEN_COLLECTOR,
    "open_collector": PinElectricalType.OPEN_COLLECTOR,
    # No connect
    "nc": PinElectricalType.NOT_CONNECTED,
    "n/c": PinElectricalType.NOT_CONNECTED,
    "-": PinElectricalType.NOT_CONNECTED,
}


def _normalize_column_name(name: str) -> str:
    """Normalize a column name for matching."""
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def _find_column(headers: list[str], candidates: list[str]) -> int | None:
    """Find the index of a column matching any of the candidates.

    Args:
        headers: List of header names
        candidates: List of candidate column names to match

    Returns:
        Column index or None if not found
    """
    normalized_headers = [_normalize_column_name(h) for h in headers]

    for candidate in candidates:
        normalized_candidate = _normalize_column_name(candidate)
        for i, header in enumerate(normalized_headers):
            if header == normalized_candidate or normalized_candidate in header:
                return i

    return None


def _parse_pin_type(type_str: str) -> PinElectricalType:
    """Parse a pin type string to PinElectricalType.

    Args:
        type_str: Type string from CSV

    Returns:
        Corresponding PinElectricalType
    """
    normalized = type_str.lower().strip()
    return TYPE_MAPPINGS.get(normalized, PinElectricalType.UNSPECIFIED)


def parse_pinout_csv(
    csv_path: str | Path,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> list[Pin]:
    """Parse a CSV file containing pinout information.

    Supports common CSV formats with flexible column naming.
    At minimum, expects pin number and pin name columns.

    Args:
        csv_path: Path to CSV file
        delimiter: CSV delimiter character
        encoding: File encoding

    Returns:
        List of Pin objects

    Raises:
        ValueError: If required columns are missing
        FileNotFoundError: If file doesn't exist
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    pins = []

    with open(path, encoding=encoding, newline="") as f:
        # Try to detect the dialect
        sample = f.read(1024)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            reader = csv.reader(f, dialect)
        except csv.Error:
            reader = csv.reader(f, delimiter=delimiter)

        # Read headers
        headers = next(reader)

        # Find required columns
        num_col = _find_column(headers, PIN_NUMBER_COLUMNS)
        name_col = _find_column(headers, PIN_NAME_COLUMNS)

        if num_col is None:
            raise ValueError(
                f"Could not find pin number column. Expected one of: {PIN_NUMBER_COLUMNS}"
            )
        if name_col is None:
            raise ValueError(
                f"Could not find pin name column. Expected one of: {PIN_NAME_COLUMNS}"
            )

        # Find optional columns
        type_col = _find_column(headers, PIN_TYPE_COLUMNS)
        desc_col = _find_column(headers, PIN_DESC_COLUMNS)
        alt_col = _find_column(headers, PIN_ALT_COLUMNS)

        # Parse rows
        for row_num, row in enumerate(reader, start=2):
            # Skip empty rows
            if not row or all(cell.strip() == "" for cell in row):
                continue

            # Get required fields
            try:
                pin_number = row[num_col].strip()
                pin_name = row[name_col].strip()
            except IndexError:
                continue  # Skip malformed rows

            if not pin_number or not pin_name:
                continue  # Skip rows with empty required fields

            # Get optional fields
            description = None
            alternates = []

            if desc_col is not None and desc_col < len(row):
                description = row[desc_col].strip() or None

            if alt_col is not None and alt_col < len(row):
                alt_str = row[alt_col].strip()
                if alt_str:
                    # Split on common separators
                    alternates = [a.strip() for a in alt_str.replace(";", ",").split(",") if a.strip()]

            # Determine electrical type
            if type_col is not None and type_col < len(row):
                type_str = row[type_col].strip()
                electrical_type = _parse_pin_type(type_str)
                if electrical_type == PinElectricalType.UNSPECIFIED:
                    # Fall back to inference
                    electrical_type = infer_pin_electrical_type(pin_name)
            else:
                electrical_type = infer_pin_electrical_type(pin_name)

            # Infer graphic style
            graphic_style = infer_pin_graphic_style(pin_name)

            pin = Pin(
                number=pin_number,
                name=pin_name,
                electrical_type=electrical_type,
                graphic_style=graphic_style,
                description=description,
                alternate_names=alternates,
            )
            pins.append(pin)

    return pins


def create_component_from_csv(
    csv_path: str | Path,
    component_name: str,
    manufacturer: str = "",
    description: str = "",
    **kwargs,
) -> ComponentInfo:
    """Create a ComponentInfo from a CSV pinout file.

    Args:
        csv_path: Path to CSV file
        component_name: Component part number
        manufacturer: Manufacturer name
        description: Component description
        **kwargs: Additional arguments passed to parse_pinout_csv

    Returns:
        ComponentInfo with pins from CSV
    """
    pins = parse_pinout_csv(csv_path, **kwargs)

    return ComponentInfo(
        name=component_name,
        manufacturer=manufacturer,
        description=description,
        pins=pins,
    )
