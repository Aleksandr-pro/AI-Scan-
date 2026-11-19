#!/usr/bin/env python3
"""Prepare a repeating 512px cobblestone tile from the supplied photograph.

Usage from the repository root:
    python minecraft/tools/prepare_cobblestone.py path/to/photo.jpg
Requires Pillow. The source photo is supplied separately and is not in the pack.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

SIZE = 512
OVERLAP = 48
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/cobblestone.png')


def blend_amount(distance):
    # Half of the opposite side at the seam; gently vanish toward the interior.
    t = 1.0 - distance / OVERLAP
    return 0.5 * t * t * (3 - 2 * t)


def prepare(source):
    image = ImageOps.exif_transpose(Image.open(source)).convert('RGB')
    # Square crop, then retain a margin for actual overlapping detail instead
    # of reflecting the edge: the two halves meet at the same source position.
    extent = SIZE + 2 * OVERLAP
    image = ImageOps.fit(image, (extent, extent), Image.Resampling.LANCZOS)
    horizontal = image.crop((OVERLAP, 0, OVERLAP + SIZE, extent))
    for d in range(OVERLAP):
        alpha = blend_amount(d)
        for x, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            source_x = x + OVERLAP
            original = image.crop((source_x, 0, source_x + 1, extent))
            opposite = image.crop((source_x + offset, 0, source_x + offset + 1, extent))
            horizontal.paste(Image.blend(original, opposite, alpha), (x, 0))
    result = horizontal.crop((0, OVERLAP, SIZE, OVERLAP + SIZE))
    for d in range(OVERLAP):
        alpha = blend_amount(d)
        for y, offset in ((d, SIZE), (SIZE - 1 - d, -SIZE)):
            source_y = y + OVERLAP
            original = horizontal.crop((0, source_y, SIZE, source_y + 1))
            opposite = horizontal.crop((0, source_y + offset, SIZE, source_y + offset + 1))
            result.paste(Image.blend(original, opposite, alpha), (0, y))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    result = prepare(args.source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT, optimize=True)
    print(f'Saved {OUTPUT}: {result.width}x{result.height} {result.mode}')


if __name__ == '__main__':
    main()
