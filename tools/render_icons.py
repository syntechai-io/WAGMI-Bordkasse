#!/usr/bin/env python3
"""Render CrewLog SVG logo to PWA icon PNGs using cairosvg."""

import os
import cairosvg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SVG_PATH = os.path.join(PROJECT_ROOT, "static", "logo-crewlog.svg")

SIZES = {
    "logo-crewlog-192.png": 192,
    "logo-crewlog-512.png": 512,
}


def render():
    for filename, size in SIZES.items():
        out = os.path.join(PROJECT_ROOT, "static", filename)
        cairosvg.svg2png(
            url=SVG_PATH,
            write_to=out,
            output_width=size,
            output_height=size,
        )
        print(f"  {filename} ({size}x{size}) -> {out}")


if __name__ == "__main__":
    print("Rendering CrewLog PWA icons from SVG...")
    render()
    print("Done.")
