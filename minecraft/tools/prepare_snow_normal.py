#!/usr/bin/env python3
"""Prepare the user's ordinary-snow photo for top, sides and bottom.

Requires Pillow; run from the repository root. Four rotations of the same
512px tile provide the existing atlas variations. Their edges match exactly,
although game filtering and block-face rotations still require in-game testing.
Powder snow and footprint overlays are deliberately untouched.
"""
from pathlib import Path
from PIL import Image
from prepare_cobblestone import prepare
from prepare_mud_concrete import match_edges

SOURCE = Path('minecraft/snow-reference/snow-normal.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')


def main():
    tile = match_edges(prepare(SOURCE), 4)
    variants = [tile, tile.transpose(Image.Transpose.ROTATE_90),
                tile.transpose(Image.Transpose.ROTATE_180),
                tile.transpose(Image.Transpose.ROTATE_270)]
    for material in ('snow', 'realistic_snow_top'):
        for i, image in enumerate(variants):
            name = material if i == 0 else f'{material}_variant_{i}'
            image.save(BLOCKS / f'{name}.png', optimize=True)
        # Build-only alias required by verify_pack.py.
        (BLOCKS / f'{material}_variant_0.png').write_bytes((BLOCKS / f'{material}.png').read_bytes())
    print('Prepared 4 ordinary-snow variants for top and sides; powder snow unchanged.')

if __name__ == '__main__':
    main()
