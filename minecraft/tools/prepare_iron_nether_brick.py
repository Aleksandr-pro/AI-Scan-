#!/usr/bin/env python3
"""Prepare the supplied iron-block and nether-brick images.

From the repository root, with Pillow installed:
    python minecraft/tools/prepare_iron_nether_brick.py iron.jpg nether_bricks.jpg
Original photographs are not included in the resource pack.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = (512, 512)


def load(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
    if image.size != (1024, 1024):
        raise ValueError(f'Expected a 1024x1024 supplied image: {path}')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iron', type=Path)
    parser.add_argument('nether_brick', type=Path)
    args = parser.parse_args()
    BLOCKS.mkdir(parents=True, exist_ok=True)

    # Keep the metal photograph's fine edge and scratches, without blending
    # the plate border or stretching the image.
    iron = load(args.iron).resize(SIZE, Image.Resampling.LANCZOS)
    iron.save(BLOCKS / 'iron_block.png', optimize=True)

    # Select four complete horizontal courses between mortar joints. Crop the
    # same width and height to retain the brick proportions without ghosting.
    brick = load(args.nether_brick).crop((47, 0, 977, 930))
    brick = brick.resize(SIZE, Image.Resampling.LANCZOS)
    brick.save(BLOCKS / 'nether_brick.png', optimize=True)
    print('Saved iron_block.png and nether_brick.png (512x512 RGB).')


if __name__ == '__main__':
    main()
