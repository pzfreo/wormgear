#!/usr/bin/env python3
"""
Generate comparison STEP files for manual CAD inspection.

Creates worm geometry using both loft and sweep methods for visual comparison.
Output goes to comparison/loft/ and comparison/sweep/ directories.

Usage:
    python scripts/generate_comparison_steps.py
    python scripts/generate_comparison_steps.py --module 2.0 --ratio 30
"""

import argparse
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wormgear.calculator.core import design_from_module
from wormgear.core.worm import WormGeometry
from build123d import export_step


def generate_pair(module, ratio, num_starts=1, hand="right", profile="ZA",
                  length=40.0, output_dir=None):
    """Generate loft and sweep STEP files for one configuration."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "comparison"

    output_dir = Path(output_dir)
    loft_dir = output_dir / "loft"
    sweep_dir = output_dir / "sweep"
    loft_dir.mkdir(parents=True, exist_ok=True)
    sweep_dir.mkdir(parents=True, exist_ok=True)

    design = design_from_module(
        module=module, ratio=ratio, num_starts=num_starts,
        hand=hand, profile=profile
    )

    filename = f"worm_m{module}_z{num_starts}_{hand}_{profile}.step"

    for method, out_dir in [("loft", loft_dir), ("sweep", sweep_dir)]:
        print(f"  Building {method}...", end=" ", flush=True)
        t0 = time.time()
        geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=length,
            sections_per_turn=72 if method == "loft" else 36,
            profile=profile,
            generation_method=method,
        )
        solid = geo.build()
        elapsed = time.time() - t0

        path = out_dir / filename
        export_step(solid, str(path))
        valid = "valid" if solid.is_valid else "INVALID"
        print(f"{elapsed:.1f}s, vol={solid.volume:.1f}mm3, {valid} -> {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate loft vs sweep comparison STEP files")
    parser.add_argument("--module", type=float, default=2.0)
    parser.add_argument("--ratio", type=int, default=30)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--all", action="store_true",
                        help="Generate full comparison matrix")
    args = parser.parse_args()

    if args.all:
        configs = [
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "right", "profile": "ZA"},
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "left", "profile": "ZA"},
            {"module": 2.0, "ratio": 15, "num_starts": 2, "hand": "right", "profile": "ZA"},
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "right", "profile": "ZK"},
            {"module": 1.0, "ratio": 30, "num_starts": 1, "hand": "right", "profile": "ZA"},
            {"module": 5.0, "ratio": 20, "num_starts": 1, "hand": "right", "profile": "ZA"},
        ]
        for cfg in configs:
            print(f"\nConfig: m={cfg['module']}, r={cfg['ratio']}, "
                  f"z={cfg['num_starts']}, {cfg['hand']}, {cfg['profile']}")
            generate_pair(output_dir=args.output_dir, **cfg)
    else:
        print(f"Config: m={args.module}, r={args.ratio}")
        generate_pair(module=args.module, ratio=args.ratio, output_dir=args.output_dir)

    print("\nDone. Compare STEP files in your CAD software.")


if __name__ == "__main__":
    main()
