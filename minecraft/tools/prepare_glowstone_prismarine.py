#!/usr/bin/env python3
"""Prepare the provided glowstone and prismarine-brick photographs.

Run from the repository root with Pillow installed:
    python minecraft/tools/prepare_glowstone_prismarine.py glowstone.jpg bricks.jpg
The original images are supplied separately and are not part of the pack.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps
from prepare_cobblestone import prepare

BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('glowstone', type=Path)
    parser.add_argument('bricks', type=Path)
    args = parser.parse_args()
    BLOCKS.mkdir(parents=True, exist_ok=True)

    # Overlap the photograph's margins to soften the natural rock seams.
    glowstone = prepare(args.glowstone)
    glowstone.save(BLOCKS / 'glowstone.png', optimize=True)

    # Keep the supplied brick courses and bevels in place. Blending opposing
    # edges would ghost the carefully aligned brick joints.
    with Image.open(args.bricks) as source:
        bricks = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),
                              (512, 512), Image.Resampling.LANCZOS)
    bricks.save(BLOCKS / 'prismarine_bricks.png', optimize=True)
    print('Saved glowstone.png and prismarine_bricks.png (512x512 RGB).')


if __name__ == '__main__':
    main()
