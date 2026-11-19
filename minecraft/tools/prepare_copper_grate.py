#!/usr/bin/env python3
"""Make the supplied copper grate's dark recesses transparent.

Run from the repository root with Pillow and NumPy installed:
    python minecraft/tools/prepare_copper_grate.py path/to/1795105383314.jpg
The photographed grid is retained; this is a texture, not a new 3D model.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/copper_grate.png')


def make_grate(source):
    with Image.open(source) as im:
        image = ImageOps.exif_transpose(im).convert('RGB')
    if image.size != (1024, 1024):
        raise ValueError('Expected the supplied 1024x1024 grate photograph')

    # Restrict each flood fill to one cell. This leaves shaded copper edges
    # and dark rivets outside the holes intact, including the clipped left edge.
    rgb = np.asarray(image)
    eligible = (rgb.max(axis=2) <= 72)
    holes = Image.new('L', image.size, 0)
    for cy in (110, 280, 450, 620, 790, 960):
        for cx in (1, 150, 350, 555, 760, 970):
            x0, y0 = max(0, cx - 82), max(0, cy - 68)
            x1, y1 = min(1024, cx + 83), min(1024, cy + 69)
            # fromarray may expose a read-only image; floodfill needs writable storage.
            window = Image.fromarray(np.where(eligible[y0:y1, x0:x1], 0, 255).astype('uint8')).copy()
            seed = (cx - x0, cy - y0)
            if window.getpixel(seed) != 0:
                raise ValueError(f'No dark hole at ({cx}, {cy})')
            ImageDraw.floodfill(window, seed, 128, thresh=0)
            selected = window.point(lambda value: 255 if value == 128 else 0)
            holes.paste(selected, (x0, y0), selected)

    # Close tiny JPEG highlights inside the connected dark recesses, then
    # antialias the cutout at source resolution. Pillow resizes RGBA using
    # premultiplied alpha to avoid dark borders around the transparency.
    holes = holes.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    holes = holes.filter(ImageFilter.GaussianBlur(0.6))
    alpha = ImageOps.invert(holes)
    rgba = image.convert('RGBA')
    rgba.putalpha(alpha)
    return rgba.resize((512, 512), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    result = make_grate(args.source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT, optimize=True)
    print(f'Saved {OUTPUT}: {result.width}x{result.height} {result.mode}')


if __name__ == '__main__':
    main()
