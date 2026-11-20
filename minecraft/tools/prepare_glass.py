#!/usr/bin/env python3
"""Extract the user's dark frame and remove its baked-in checkerboard.

Run from the repository root: python minecraft/tools/prepare_glass.py
Requires Pillow. The source is an RGB image: the checkerboard is not alpha.
The explicitly measured boxes apply only to the supplied source image.
"""
from pathlib import Path
from PIL import Image, ImageDraw

SOURCE = Path('minecraft/glass-reference/frame.png')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/realistic_clear_glass.png')
SIZE = 512
# Source-pixel coordinates, left/top inclusive and right/bottom exclusive.
OUTER = (13, 9, 1241, 1242)
INNER = (56, 52, 1199, 1199)


def prepare(source=SOURCE):
    with Image.open(source) as original:
        if original.size != (1254, 1254):
            raise ValueError('Expected the original 1254x1254 frame photograph')
        image = original.convert('RGB').convert('RGBA')
    alpha = Image.new('L', image.size, 255)
    draw = ImageDraw.Draw(alpha)
    # Pillow rectangles include the last pixel; INNER is exclusive.
    draw.rectangle((INNER[0], INNER[1], INNER[2] - 1, INNER[3] - 1), fill=0)
    image.putalpha(alpha)
    image = image.crop(OUTER)
    # Pillow uses premultiplied-alpha resizing for RGBA, avoiding a white
    # checkerboard fringe where the opaque frame meets the transparent centre.
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared transparent framed glass: {OUTPUT}')


if __name__ == '__main__':
    main()
