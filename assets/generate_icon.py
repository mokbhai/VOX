#!/usr/bin/env python3
"""Generate .icns file from SVG logo for Vox app."""

import subprocess
import shutil
from pathlib import Path

# Paths
ASSETS_DIR = Path(__file__).parent
SVG_FILE = ASSETS_DIR / "logo.svg"
ICONSET_DIR = ASSETS_DIR / "logo.iconset"
ICNS_FILE = ASSETS_DIR / "logo.icns"

# Required sizes for macOS iconset
SIZES = [16, 32, 64, 128, 256, 512]

def main():
    # Create iconset directory
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir()

    # Check if we have rsvg-convert or use sips with a PNG first
    # Try to convert SVG to PNG using available tools

    # First, create a high-res PNG using rsvg-convert if available
    try:
        # Check for rsvg-convert
        subprocess.run(["which", "rsvg-convert"], check=True, capture_output=True)

        # Generate all required sizes
        for size in SIZES:
            # Regular size
            output = ICONSET_DIR / f"icon_{size}x{size}.png"
            subprocess.run([
                "rsvg-convert", "-w", str(size), "-h", str(size),
                "-o", str(output), str(SVG_FILE)
            ], check=True)

            # Retina size (2x)
            if size <= 256:
                retina_size = size * 2
                output_2x = ICONSET_DIR / f"icon_{size}x{size}@2x.png"
                subprocess.run([
                    "rsvg-convert", "-w", str(retina_size), "-h", str(retina_size),
                    "-o", str(output_2x), str(SVG_FILE)
                ], check=True)

    except subprocess.CalledProcessError:
        print("rsvg-convert not found. Trying with cairosvg...")

        # Try cairosvg as fallback
        try:
            import cairosvg

            for size in SIZES:
                output = ICONSET_DIR / f"icon_{size}x{size}.png"
                cairosvg.svg2png(
                    url=str(SVG_FILE),
                    write_to=str(output),
                    output_width=size,
                    output_height=size
                )

                if size <= 256:
                    retina_size = size * 2
                    output_2x = ICONSET_DIR / f"icon_{size}x{size}@2x.png"
                    cairosvg.svg2png(
                        url=str(SVG_FILE),
                        write_to=str(output_2x),
                        output_width=retina_size,
                        output_height=retina_size
                    )
        except ImportError:
            print("cairosvg not found either. Please install librsvg or cairosvg.")
            print("Run: brew install librsvg")
            print("Or: uv add cairosvg")
            return 1

    # Generate .icns using iconutil
    print("Generating .icns file...")
    subprocess.run([
        "iconutil", "-c", "icns",
        "-o", str(ICNS_FILE),
        str(ICONSET_DIR)
    ], check=True)

    print(f"Successfully created {ICNS_FILE}")

    # Clean up iconset directory
    shutil.rmtree(ICONSET_DIR)

    return 0

if __name__ == "__main__":
    exit(main())
