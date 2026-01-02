# KiForge

Automatic KiCad component generator from datasheets.

## Overview

KiForge extracts component information from datasheets and generates complete KiCad components:

```
Inputs                          Outputs
──────                          ───────
• Datasheet (PDF)        ──►    • Schematic symbol (.kicad_sym)
• Pinout table (CSV)     ──►    • Footprint (.kicad_mod)
• Eval board datasheet   ──►    • 3D model (.step)
```

## Features

- **PDF parsing** via [Docling](https://github.com/docling-project/docling) - extracts pin tables, package dimensions, electrical specifications
- **Parametric footprint generation** - supports common package types (QFP, QFN, BGA, SOIC, DIP, etc.)
- **Parametric 3D model generation** - creates STEP models from package dimensions
- **Symbol generation** - multi-unit symbols with proper pin types and grouping

## Installation

```bash
pip install kiforge
```

Or from source:

```bash
git clone git@github.com:Ka-zam/KiForge.git
cd KiForge
pip install -e .
```

## Dependencies

- Python 3.10+
- PyQt6
- docling
- cadquery (for 3D model generation)

## Usage

```bash
kiforge
```

Launch the GUI and:
1. Load component datasheet (PDF)
2. Optionally load pinout CSV for manual pin definitions
3. Optionally load eval board datasheet for additional context
4. Review extracted information
5. Generate symbol, footprint, and 3D model

## Project Structure

```
kiforge/
├── core/
│   ├── parser/          # Docling-based PDF parsing
│   ├── symbol/          # Schematic symbol generation
│   ├── footprint/       # Footprint generation
│   └── model3d/         # 3D STEP model generation
├── gui/                 # Qt6 interface
└── data/
    └── packages/        # Package dimension templates
```

## License

GPL-2.0 - see [LICENSE](LICENSE)
