"""
Wormgear CLI - Command-line interfaces.

This module provides CLI commands for both calculation and generation.

Commands:
    calculate    Calculate parameters from inputs → JSON
    generate     Generate 3D models from JSON → STEP files
    validate     Validate JSON design file
    spec         Generate engineering specifications

Example:
    $ wormgear calculate --module 2.0 --ratio 30 --output design.json
    $ wormgear generate design.json
    $ wormgear validate design.json
"""

# CLI will be implemented using Typer
# - calculate.py - Calculator CLI (from wormgearcalc)
# - generate.py - Geometry generator CLI (from cli.py)
# - main.py - Unified entry point

__all__ = []
