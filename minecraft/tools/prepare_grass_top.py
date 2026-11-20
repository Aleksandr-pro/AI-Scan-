#!/usr/bin/env python3
"""Prepare four supplied grass-block top photographs; requires Pillow.

From the repository root: python minecraft/tools/prepare_grass_top.py
The ordered user originals are in minecraft/grass-top-reference/. This writes
one grass_top.png and three grass_top_variant_*.png files without duplicates.
"""
from pathlib import Path
from PIL import Image
from prepare_cobblestone import prepare, SIZE

ROOT = Path('minecraft')
SOURCES = ROOT / 'grass-top-reference'
BLOCKS = ROOT / 'realistic-dirt/textures/blocks'
FILES = ('01_sparse.jpg', '02_sparse.jpg', '03_grassy.jpg', '04_dense.jpg')
EDGE_WIDTH = 20


def main():
    # First make each source repeat smoothly in both directions.
    tiles = [prepare(SOURCES / filename) for filename in FILES]
    # Use the moderately grassy photograph for a common narrow border. This
    # preserves its sharp detail rather than averaging four unrelated photos,
    # which would leave a blurred frame around every block. Interiors stay
    # faithful to each of the four supplied references.
    common = tiles[2]
    weights = []
    for y in range(SIZE):
        for x in range(SIZE):
            distance = min(x, y, SIZE - 1 - x, SIZE - 1 - y)
            t = min(1.0, distance / EDGE_WIDTH)
            weights.append(round(255 * t * t * (3 - 2 * t)))
    mask = Image.new('L', (SIZE, SIZE))
    mask.putdata(weights)
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i, tile in enumerate(tiles):
        result = Image.composite(tile, common, mask)
        name = 'grass_top.png' if i == 0 else f'grass_top_variant_{i}.png'
        result.save(BLOCKS / name, optimize=True)
    print('Prepared four distinct 512x512 RGB grass tops; sides unchanged.')


if __name__ == '__main__':
    main()
