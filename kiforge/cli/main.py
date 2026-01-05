"""KiForge CLI application."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="kiforge",
    help="Automatic KiCad component generator from datasheets.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def version() -> None:
    """Show version information."""
    from kiforge import __version__

    console.print(f"KiForge v{__version__}")


@app.command()
def footprint(
    package: str = typer.Argument(..., help="Package type (e.g., LQFP, QFN, BGA)"),
    pins: int = typer.Option(..., "--pins", "-p", help="Number of pins"),
    pitch: float = typer.Option(..., "--pitch", help="Pin pitch in mm"),
    body: str = typer.Option(..., "--body", "-b", help="Body size WxH in mm (e.g., 7x7)"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    lead_span: float | None = typer.Option(None, "--lead-span", help="Lead span in mm (QFP only, default: body + 2mm)"),
    thermal_pad: float | None = typer.Option(None, "--thermal-pad", "-t", help="Thermal pad size in mm (QFN only)"),
) -> None:
    """Generate a parametric footprint."""
    from kiforge.core.footprint.qfp import create_qfp_footprint
    from kiforge.core.footprint.qfn import create_qfn_footprint

    # Parse body dimensions
    try:
        if "x" in body.lower():
            parts = body.lower().split("x")
            body_w = float(parts[0])
            body_h = float(parts[1])
        else:
            body_w = body_h = float(body)
    except ValueError:
        console.print(f"[red]Invalid body size format: {body}[/red]")
        console.print("Expected format: WxH (e.g., 7x7 or 10x10)")
        raise typer.Exit(1)

    package_upper = package.upper()

    console.print(f"Generating [cyan]{package_upper}-{pins}[/cyan] footprint:")
    console.print(f"  Pitch: {pitch}mm")
    console.print(f"  Body: {body_w}x{body_h}mm")

    # Generate based on package type
    if package_upper in ("QFP", "LQFP", "TQFP", "VQFP"):
        # Calculate lead span if not specified
        if lead_span is None:
            lead_span = max(body_w, body_h) + 2.0  # Add 2mm for leads

        console.print(f"  Lead span: {lead_span}mm")

        try:
            content = create_qfp_footprint(
                pins=pins,
                pitch=pitch,
                body_width=body_w,
                body_length=body_h,
                lead_span=lead_span,
                variant=package_upper,
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Write output
        output_path = output / f"{package_upper}-{pins}_{body_w}x{body_h}mm_P{pitch}mm.kicad_mod"
        output.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

        console.print(f"[green]Created:[/green] {output_path}")

    elif package_upper in ("QFN", "DFN", "VQFN", "WQFN"):
        if thermal_pad is not None:
            console.print(f"  Thermal pad: {thermal_pad}x{thermal_pad}mm")

        try:
            content = create_qfn_footprint(
                pins=pins,
                pitch=pitch,
                body_width=body_w,
                body_length=body_h,
                thermal_pad_size=thermal_pad,
                variant=package_upper,
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Write output
        ep_str = f"_EP{thermal_pad}x{thermal_pad}mm" if thermal_pad else ""
        output_path = output / f"{package_upper}-{pins}_{body_w}x{body_h}mm_P{pitch}mm{ep_str}.kicad_mod"
        output.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

        console.print(f"[green]Created:[/green] {output_path}")

    else:
        console.print(f"[yellow]Package type {package_upper} not yet implemented[/yellow]")
        console.print("Supported packages: QFP, LQFP, TQFP, VQFP, QFN, DFN, VQFN, WQFN")
        raise typer.Exit(1)


@app.command()
def symbol(
    pinout: Path = typer.Argument(..., help="Pinout CSV file"),
    name: str = typer.Option(..., "--name", "-n", help="Component part number"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    manufacturer: str = typer.Option("", "--manufacturer", "-m", help="Manufacturer name"),
    description: str = typer.Option("", "--description", "-d", help="Component description"),
) -> None:
    """Generate a schematic symbol from a CSV pinout file."""
    from kiforge.core.parser import create_component_from_csv
    from kiforge.core.symbol import create_symbol

    if not pinout.exists():
        console.print(f"[red]File not found: {pinout}[/red]")
        raise typer.Exit(1)

    console.print(f"Parsing pinout from [cyan]{pinout}[/cyan]")

    try:
        component = create_component_from_csv(
            pinout,
            component_name=name,
            manufacturer=manufacturer,
            description=description,
        )
    except ValueError as e:
        console.print(f"[red]Error parsing CSV: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"Found [green]{len(component.pins)}[/green] pins")

    # Show pin summary
    table = Table(title="Pin Summary")
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")

    from collections import Counter
    type_counts = Counter(p.electrical_type.value for p in component.pins)
    for ptype, count in sorted(type_counts.items()):
        table.add_row(ptype, str(count))

    console.print(table)

    # Generate symbol
    content = create_symbol(component)

    # Write output
    output.mkdir(parents=True, exist_ok=True)
    output_path = output / f"{name}.kicad_sym"
    output_path.write_text(content)

    console.print(f"[green]Created:[/green] {output_path}")


@app.command()
def generate(
    pinout: Path = typer.Argument(..., help="Pinout CSV file"),
    name: str = typer.Option(..., "--name", "-n", help="Component part number"),
    package: str = typer.Option(..., "--package", "-p", help="Package type (e.g., LQFP-64)"),
    pitch: float = typer.Option(..., "--pitch", help="Pin pitch in mm"),
    body: str = typer.Option(..., "--body", "-b", help="Body size WxH in mm"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    manufacturer: str = typer.Option("", "--manufacturer", "-m", help="Manufacturer name"),
) -> None:
    """Generate symbol and footprint from a CSV pinout file."""
    from kiforge.core.footprint.qfp import create_qfp_footprint
    from kiforge.core.parser import create_component_from_csv
    from kiforge.core.symbol import create_symbol

    if not pinout.exists():
        console.print(f"[red]File not found: {pinout}[/red]")
        raise typer.Exit(1)

    # Parse body dimensions
    try:
        if "x" in body.lower():
            parts = body.lower().split("x")
            body_w = float(parts[0])
            body_h = float(parts[1])
        else:
            body_w = body_h = float(body)
    except ValueError:
        console.print(f"[red]Invalid body size format: {body}[/red]")
        raise typer.Exit(1)

    # Parse package type and pin count
    package_upper = package.upper()
    pkg_parts = package_upper.replace("-", " ").replace("_", " ").split()
    pkg_type = pkg_parts[0]

    # Create component from CSV
    console.print(f"Parsing pinout from [cyan]{pinout}[/cyan]")

    try:
        component = create_component_from_csv(
            pinout,
            component_name=name,
            manufacturer=manufacturer,
        )
    except ValueError as e:
        console.print(f"[red]Error parsing CSV: {e}[/red]")
        raise typer.Exit(1)

    pins = len(component.pins)
    console.print(f"Found [green]{pins}[/green] pins")

    output.mkdir(parents=True, exist_ok=True)

    # Generate symbol
    console.print("Generating symbol...")
    symbol_content = create_symbol(component)
    symbol_path = output / f"{name}.kicad_sym"
    symbol_path.write_text(symbol_content)
    console.print(f"  [green]Created:[/green] {symbol_path}")

    # Generate footprint
    if pkg_type in ("QFP", "LQFP", "TQFP", "VQFP"):
        console.print("Generating footprint...")
        lead_span = max(body_w, body_h) + 2.0

        try:
            footprint_content = create_qfp_footprint(
                pins=pins,
                pitch=pitch,
                body_width=body_w,
                body_length=body_h,
                lead_span=lead_span,
                variant=pkg_type,
            )
            footprint_path = output / f"{pkg_type}-{pins}_{body_w}x{body_h}mm_P{pitch}mm.kicad_mod"
            footprint_path.write_text(footprint_content)
            console.print(f"  [green]Created:[/green] {footprint_path}")
        except ValueError as e:
            console.print(f"  [yellow]Skipped footprint: {e}[/yellow]")
    elif pkg_type in ("QFN", "DFN", "VQFN", "WQFN"):
        from kiforge.core.footprint.qfn import create_qfn_footprint

        console.print("Generating footprint...")
        try:
            footprint_content = create_qfn_footprint(
                pins=pins,
                pitch=pitch,
                body_width=body_w,
                body_length=body_h,
                variant=pkg_type,
            )
            footprint_path = output / f"{pkg_type}-{pins}_{body_w}x{body_h}mm_P{pitch}mm.kicad_mod"
            footprint_path.write_text(footprint_content)
            console.print(f"  [green]Created:[/green] {footprint_path}")
        except ValueError as e:
            console.print(f"  [yellow]Skipped footprint: {e}[/yellow]")
    else:
        console.print(f"  [yellow]Footprint for {pkg_type} not yet implemented[/yellow]")

    console.print("[green]Done![/green]")


@app.command()
def pins(
    pinout: Path = typer.Argument(..., help="Pinout CSV file"),
) -> None:
    """Display pins from a CSV file."""
    from kiforge.core.parser import parse_pinout_csv

    if not pinout.exists():
        console.print(f"[red]File not found: {pinout}[/red]")
        raise typer.Exit(1)

    try:
        pins = parse_pinout_csv(pinout)
    except ValueError as e:
        console.print(f"[red]Error parsing CSV: {e}[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Pins from {pinout.name}")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Style")
    table.add_column("Alternates", style="dim")

    for pin in pins:
        alternates = ", ".join(pin.alternate_names[:3])
        if len(pin.alternate_names) > 3:
            alternates += f" (+{len(pin.alternate_names) - 3})"

        table.add_row(
            pin.number,
            pin.name,
            pin.electrical_type.value,
            pin.graphic_style.value,
            alternates,
        )

    console.print(table)
    console.print(f"\nTotal: [green]{len(pins)}[/green] pins")


@app.command()
def info() -> None:
    """Show supported package types and features."""
    console.print("[bold]KiForge - KiCad Component Generator[/bold]\n")

    console.print("[cyan]Supported Package Types:[/cyan]")
    console.print("  Footprint generation:")
    console.print("    - QFP, LQFP, TQFP, VQFP (Quad Flat Package)")
    console.print("    - QFN, DFN, VQFN, WQFN (Quad Flat No-lead)")
    console.print("    - [dim]BGA, FBGA, WLCSP (coming soon)[/dim]")
    console.print("")

    console.print("[cyan]Input Formats:[/cyan]")
    console.print("  - CSV pinout files (pin number, name, type)")
    console.print("  - [dim]PDF datasheets (coming soon, requires docling)[/dim]")
    console.print("")

    console.print("[cyan]Output Formats:[/cyan]")
    console.print("  - KiCad 8 schematic symbols (.kicad_sym)")
    console.print("  - KiCad 8 footprints (.kicad_mod)")
    console.print("  - [dim]3D STEP models (coming soon, requires cadquery)[/dim]")


if __name__ == "__main__":
    app()
