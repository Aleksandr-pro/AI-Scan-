#!/usr/bin/env python3
"""Prepare four two-block grass photos from two black-background screenshots.

Run from repo root. Requires Pillow and numpy. The seam band is shared across
variants to reduce mismatched upper/lower joins if Bedrock selects independently.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT = Path('minecraft')
SOURCES = (ROOT / 'tall-grass-reference/two-plants-01.jpg', ROOT / 'tall-grass-reference/two-plants-02.jpg')
BLOCKS = ROOT / 'realistic-dirt/textures/blocks'
SIZE = 256
HEIGHT = SIZE * 2
JOIN_BAND = 20
JOIN_CORE = 3


def extract(source, half):
    with Image.open(source) as im:
        image = ImageOps.exif_transpose(im).convert('RGB')
        width, height = image.size
        x0, x1 = (0, width // 2) if half == 0 else (width // 2, width)
        rgb = np.asarray(image.crop((x0, 0, x1, height)), dtype=np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    solid = (g > 14) & (g > r * 1.1) & (g > b * 1.1)
    ys, xs = np.where(solid)
    if not len(xs):
        raise ValueError(f'No green plant found in {source} half {half}')
    # Bounds come from visible plant material, expanded for antialiased edges.
    left, right = max(0, int(xs.min())-5), min(rgb.shape[1], int(xs.max())+6)
    top, bottom = max(0, int(ys.min())-5), min(rgb.shape[0], int(ys.max())+6)
    rgb = rgb[top:bottom, left:right]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    alpha = np.clip((g - 5) / 22, 0, 1)
    # Black screenshot backdrop and low-level JPEG noise are not foreground.
    alpha = np.where(g > np.maximum(r, b) + 1, alpha, 0)
    safe = np.maximum(alpha, 1/255)[..., None]
    colors = np.clip(rgb / safe, 0, 255).astype(np.uint8)
    pixels = np.dstack((colors, np.rint(alpha * 255).astype(np.uint8)))
    pixels[pixels[..., 3] == 0, :3] = 0
    plant = Image.fromarray(pixels, 'RGBA')
    # Preserve the height-to-width proportion while filling almost two blocks.
    plant.thumbnail((SIZE - 8, HEIGHT - 12), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, HEIGHT), (0, 0, 0, 0))
    canvas.paste(plant, ((SIZE - plant.width)//2, HEIGHT - 6 - plant.height))
    return canvas


def prepared_plants():
    plants = [extract(source, half) for source in SOURCES for half in (0, 1)]
    common = plants[0]
    results = []
    for plant in plants:
        fixed = plant.copy()
        for y in range(SIZE-JOIN_BAND, SIZE+JOIN_BAND):
            distance = abs(y + .5 - SIZE)
            # Identical narrow core at the join, then fade over 20 pixels.
            weight = max(0, min(1, (JOIN_BAND - distance)/(JOIN_BAND-JOIN_CORE)))
            if weight:
                row = plant.crop((0, y, SIZE, y+1))
                ref = common.crop((0, y, SIZE, y+1))
                fixed.paste(Image.blend(row, ref, weight), (0, y))
        results.append(fixed)
    return results


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i, plant in enumerate(prepared_plants()):
        # First pair uses the vanilla filenames for older double_plant atlas.
        suffix = '' if i == 0 else f'_variant_{i}'
        plant.crop((0, 0, SIZE, SIZE)).save(BLOCKS / f'double_plant_grass_top{suffix}.png', optimize=True)
        plant.crop((0, SIZE, SIZE, HEIGHT)).save(BLOCKS / f'double_plant_grass_bottom{suffix}.png', optimize=True)
    print('Prepared 4 two-block grass variants (8 half textures).')


if __name__ == '__main__':
    main()
