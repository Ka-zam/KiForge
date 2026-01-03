"""Enumerations for KiForge data models."""

from enum import Enum


class PinElectricalType(str, Enum):
    """KiCad pin electrical types for ERC (Electrical Rule Check).

    These map directly to KiCad's internal pin types and are used for
    electrical rule checking in schematics.
    """

    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRISTATE = "tri_state"
    PASSIVE = "passive"
    FREE = "free"  # Not internally connected
    UNSPECIFIED = "unspecified"
    POWER_INPUT = "power_in"  # VCC, GND supply pins
    POWER_OUTPUT = "power_out"  # Regulator output, etc.
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    NOT_CONNECTED = "no_connect"  # NC pins - must be left open


class PinGraphicStyle(str, Enum):
    """KiCad pin graphic styles for schematic display."""

    LINE = "line"  # Standard line
    INVERTED = "inverted"  # Hollow circle (active low)
    CLOCK = "clock"  # Clock input triangle
    INVERTED_CLOCK = "inverted_clock"
    INPUT_LOW = "input_low"  # IEEE low input
    CLOCK_LOW = "clock_low"
    OUTPUT_LOW = "output_low"  # IEEE low output
    EDGE_CLOCK_HIGH = "edge_clock_high"
    NON_LOGIC = "non_logic"


class PinOrientation(str, Enum):
    """Pin direction on symbol (direction connection points INTO symbol).

    The value is the angle in degrees for KiCad's S-expression format:
    - 0 = Pin points right (connection on left side of symbol)
    - 90 = Pin points up (connection on bottom of symbol)
    - 180 = Pin points left (connection on right side of symbol)
    - 270 = Pin points down (connection on top of symbol)
    """

    RIGHT = "0"  # Pin on left side, pointing right
    UP = "90"  # Pin on bottom, pointing up
    LEFT = "180"  # Pin on right side, pointing left
    DOWN = "270"  # Pin on top, pointing down


class PinGroupCategory(str, Enum):
    """Logical categories for pin grouping in symbols."""

    POWER = "power"  # VCC, VDD
    GROUND = "ground"  # GND, VSS
    INPUT = "input"  # General inputs
    OUTPUT = "output"  # General outputs
    BIDIRECTIONAL = "bidirectional"  # I/O pins
    CONTROL = "control"  # Enable, reset, chip select
    CLOCK = "clock"  # Clock inputs/outputs
    ANALOG = "analog"  # ADC, DAC, analog I/O
    COMMUNICATION = "communication"  # SPI, I2C, UART, etc.
    DEBUG = "debug"  # JTAG, SWD, etc.
    NC = "nc"  # Not connected
    OTHER = "other"


class PackageType(str, Enum):
    """Supported IC package families."""

    # Quad packages (4-sided)
    QFP = "QFP"  # Quad Flat Package (gull-wing leads)
    LQFP = "LQFP"  # Low-profile QFP (height <= 1.6mm)
    TQFP = "TQFP"  # Thin QFP (height <= 1.0mm)
    VQFP = "VQFP"  # Very thin QFP
    QFN = "QFN"  # Quad Flat No-lead
    VQFN = "VQFN"  # Very thin QFN
    WQFN = "WQFN"  # Wettable flank QFN
    DFN = "DFN"  # Dual Flat No-lead (2-sided)

    # Array packages
    BGA = "BGA"  # Ball Grid Array
    FBGA = "FBGA"  # Fine-pitch BGA
    TFBGA = "TFBGA"  # Thin Fine-pitch BGA
    UFBGA = "UFBGA"  # Ultra Fine-pitch BGA
    WLCSP = "WLCSP"  # Wafer Level Chip Scale Package
    DSBGA = "DSBGA"  # Die-Size BGA

    # Dual packages (2-sided)
    SOIC = "SOIC"  # Small Outline IC
    SOP = "SOP"  # Small Outline Package
    SSOP = "SSOP"  # Shrink SOP
    TSSOP = "TSSOP"  # Thin Shrink SOP
    MSOP = "MSOP"  # Mini SOP
    DIP = "DIP"  # Dual In-line Package (through-hole)

    # Single-row / small packages
    SOT = "SOT"  # Small Outline Transistor
    SOT23 = "SOT-23"
    SOT223 = "SOT-223"
    TO = "TO"  # Transistor Outline
    SC70 = "SC-70"


class PadShape(str, Enum):
    """PCB pad shapes for footprints."""

    RECTANGLE = "rect"
    ROUNDRECT = "roundrect"
    OVAL = "oval"
    CIRCLE = "circle"
    TRAPEZOID = "trapezoid"
    CUSTOM = "custom"


class PadType(str, Enum):
    """PCB pad types."""

    SMD = "smd"
    THRU_HOLE = "thru_hole"
    NPTH = "np_thru_hole"  # Non-plated through hole
    CONNECT = "connect"  # Edge connector


class BGABallPattern(str, Enum):
    """BGA ball array patterns."""

    FULL_MATRIX = "full"  # All positions populated
    PERIMETER = "perimeter"  # Only outer rings
    STAGGERED = "staggered"  # Alternating positions
    DEPOPULATED_CENTER = "depop_center"  # Center region empty (moat)
    CUSTOM = "custom"  # Custom pattern with explicit mask
