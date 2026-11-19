#!/usr/bin/env python3
"""Prepare a repeating 512px cobblestone tile from a supplied photograph.

Usage from the repository root:
    python minecraft/tools/prepare_cobblestone.py path/to/normal.jpg
    python minecraft/tools/prepare_cobblestone.py path/to/mossy.jpg --mossy
Requires Pillow. Source photos are supplied separately and are not in the pack.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

SIZE = 512
OVERLAP = 48
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')


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
    parser.add_argument('--mossy', action='store_true', help='write the mossy vanilla texture instead')
    args = parser.parse_args()
    result = prepare(args.source)
    output = BLOCKS / ('cobblestone_mossy.png' if args.mossy else 'cobblestone.png')
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, optimize=True)
    print(f'Saved {output}: {result.width}x{result.height} {result.mode}')


if __name__ == '__main__':
    main()
