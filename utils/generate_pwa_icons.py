#!/usr/bin/env python3
"""
Generate PNG icons from SVG for PWA installation.
Requires: cairosvg (pip install cairosvg)
"""

import os
from pathlib import Path

def generate_icons():
    """Generate 192x192 and 512x512 PNG icons from SVG."""
    try:
        import cairosvg
    except ImportError:
        print("❌ cairosvg not installed. Install with: pip install cairosvg")
        print("   Alternatively, use an online SVG-to-PNG converter or Inkscape CLI.")
        return False
    
    base_dir = Path(__file__).parent.parent / "static" / "icons"
    svg_path = base_dir / "candlestick-icon.svg"
    
    if not svg_path.exists():
        print(f"❌ SVG file not found: {svg_path}")
        return False
    
    sizes = [192, 512]
    
    for size in sizes:
        png_path = base_dir / f"candlestick-icon-{size}.png"
        print(f"Generating {size}×{size} PNG: {png_path}")
        
        try:
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(png_path),
                output_width=size,
                output_height=size
            )
            print(f"✅ Created: {png_path}")
        except Exception as e:
            print(f"❌ Error generating {size}×{size}: {e}")
            return False
    
    print("\n✅ All PNG icons generated successfully!")
    print(f"   Icons saved to: {base_dir}")
    return True

if __name__ == "__main__":
    generate_icons()
