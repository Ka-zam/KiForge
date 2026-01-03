"""Pin type inference from names and context."""

from kiforge.core.models.enums import PinElectricalType, PinGraphicStyle, PinGroupCategory


def infer_pin_electrical_type(pin_name: str) -> PinElectricalType:
    """Infer electrical type from pin name.

    Uses common naming conventions to guess the electrical type of a pin.

    Args:
        pin_name: Pin name string

    Returns:
        Best-guess PinElectricalType
    """
    name = pin_name.upper().strip()

    # Power supply pins
    power_patterns = ["VCC", "VDD", "VBAT", "AVDD", "DVDD", "V+", "VIN", "VCORE", "VCCA", "VCCD"]
    if any(name == pat or name.startswith(pat + "_") or name.startswith(pat) for pat in power_patterns):
        return PinElectricalType.POWER_INPUT

    # Ground pins
    ground_patterns = ["GND", "VSS", "AVSS", "DVSS", "AGND", "DGND", "V-", "PGND", "GNDA", "GNDD"]
    if any(name == pat or name.startswith(pat + "_") or name.startswith(pat) for pat in ground_patterns):
        return PinElectricalType.POWER_INPUT

    # NC pins (no connect)
    nc_patterns = ["NC", "N/C", "DNC", "N.C.", "RSVD", "RESERVED"]
    if any(name == pat or name.startswith(pat) for pat in nc_patterns):
        return PinElectricalType.NOT_CONNECTED

    # Clock pins (typically input)
    clock_patterns = ["CLK", "CLOCK", "OSC", "XTAL", "EXTAL", "XI", "XO", "CLKIN"]
    if any(name == pat or name.startswith(pat + "_") or name.startswith(pat) for pat in clock_patterns):
        return PinElectricalType.INPUT

    # Reset pins (typically input, active low)
    reset_patterns = ["RST", "RESET", "NRST", "~RST", "RSTN", "MR", "MCLR"]
    if any(name == pat or name.startswith(pat + "_") or name.startswith(pat) for pat in reset_patterns):
        return PinElectricalType.INPUT

    # Output indicators
    output_patterns = ["OUT", "TXD", "TX", "MOSI", "SCK", "SCLK", "DO", "DOUT", "SDO", "TDO"]
    if any(name == pat or name.endswith("_" + pat) or name.startswith(pat) for pat in output_patterns):
        return PinElectricalType.OUTPUT

    # Input indicators
    input_patterns = ["IN", "RXD", "RX", "MISO", "DI", "DIN", "SDI", "TDI", "TCK", "TMS"]
    if any(name == pat or name.endswith("_" + pat) or name.startswith(pat) for pat in input_patterns):
        return PinElectricalType.INPUT

    # GPIO / Port pins (bidirectional)
    gpio_patterns = ["GPIO", "PORT", "IO", "P0", "P1", "P2", "P3", "PA", "PB", "PC", "PD", "PE", "PF"]
    if any(name.startswith(pat) for pat in gpio_patterns):
        return PinElectricalType.BIDIRECTIONAL

    # SDA/SWD are bidirectional
    bidir_patterns = ["SDA", "SWDIO", "D+", "D-", "DP", "DM", "USB"]
    if any(name == pat or name.startswith(pat) for pat in bidir_patterns):
        return PinElectricalType.BIDIRECTIONAL

    # Open drain outputs (interrupts often open-drain)
    od_patterns = ["INT", "IRQ", "NMI", "ALERT", "BUSY"]
    if any(name.startswith(pat) for pat in od_patterns):
        return PinElectricalType.OPEN_COLLECTOR

    # Analog pins
    analog_patterns = ["AIN", "AOUT", "ADC", "DAC", "VREF", "AN"]
    if any(name.startswith(pat) for pat in analog_patterns):
        return PinElectricalType.PASSIVE

    # Default: unspecified
    return PinElectricalType.UNSPECIFIED


def infer_pin_graphic_style(pin_name: str) -> PinGraphicStyle:
    """Infer graphic style from pin name conventions.

    Args:
        pin_name: Pin name string

    Returns:
        Best-guess PinGraphicStyle
    """
    name = pin_name.upper().strip()

    # Active-low indicators
    if name.startswith("~") or name.startswith("/"):
        return PinGraphicStyle.INVERTED
    if name.startswith("N") and len(name) > 1 and name[1].isupper():
        # NRST, NCS, etc.
        return PinGraphicStyle.INVERTED
    if name.endswith("_N") or name.endswith("_B") or name.endswith("#"):
        return PinGraphicStyle.INVERTED

    # Clock pins
    clock_patterns = ["CLK", "CLOCK", "SCK", "SCLK", "TCK"]
    if any(name == pat or name.endswith("_" + pat) for pat in clock_patterns):
        return PinGraphicStyle.CLOCK

    return PinGraphicStyle.LINE


def infer_pin_group_category(pin_name: str, electrical_type: PinElectricalType) -> PinGroupCategory:
    """Infer pin group category from name and electrical type.

    Args:
        pin_name: Pin name string
        electrical_type: Electrical type of the pin

    Returns:
        Best-guess PinGroupCategory
    """
    name = pin_name.upper().strip()

    # Check electrical type first
    if electrical_type == PinElectricalType.NOT_CONNECTED:
        return PinGroupCategory.NC

    # Power and ground
    power_patterns = ["VCC", "VDD", "VBAT", "AVDD", "DVDD", "V+", "VIN", "VCORE"]
    if any(name.startswith(pat) for pat in power_patterns):
        return PinGroupCategory.POWER

    ground_patterns = ["GND", "VSS", "AVSS", "DVSS", "AGND", "DGND", "V-"]
    if any(name.startswith(pat) for pat in ground_patterns):
        return PinGroupCategory.GROUND

    # Communication interfaces
    comm_patterns = ["SPI", "I2C", "UART", "USART", "CAN", "USB", "ETH", "MOSI", "MISO", "SCL", "SDA", "TX", "RX"]
    if any(name.startswith(pat) for pat in comm_patterns):
        return PinGroupCategory.COMMUNICATION

    # Debug interfaces
    debug_patterns = ["JTAG", "SWD", "TDI", "TDO", "TCK", "TMS", "TRST", "SWDIO", "SWCLK"]
    if any(name.startswith(pat) for pat in debug_patterns):
        return PinGroupCategory.DEBUG

    # Clock
    clock_patterns = ["CLK", "CLOCK", "OSC", "XTAL"]
    if any(name.startswith(pat) for pat in clock_patterns):
        return PinGroupCategory.CLOCK

    # Control signals
    ctrl_patterns = ["EN", "ENABLE", "RST", "RESET", "CS", "CE", "WR", "RD", "OE", "WE"]
    if any(name.startswith(pat) for pat in ctrl_patterns):
        return PinGroupCategory.CONTROL

    # Analog
    analog_patterns = ["AIN", "AOUT", "ADC", "DAC", "VREF", "AN"]
    if any(name.startswith(pat) for pat in analog_patterns):
        return PinGroupCategory.ANALOG

    # GPIO (bidirectional)
    gpio_patterns = ["GPIO", "PORT", "IO", "P0", "P1", "PA", "PB"]
    if any(name.startswith(pat) for pat in gpio_patterns):
        return PinGroupCategory.BIDIRECTIONAL

    # By electrical type
    if electrical_type == PinElectricalType.INPUT:
        return PinGroupCategory.INPUT
    if electrical_type == PinElectricalType.OUTPUT:
        return PinGroupCategory.OUTPUT
    if electrical_type == PinElectricalType.BIDIRECTIONAL:
        return PinGroupCategory.BIDIRECTIONAL

    return PinGroupCategory.OTHER
