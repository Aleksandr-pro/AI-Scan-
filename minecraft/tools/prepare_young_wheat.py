#!/usr/bin/env python3
"""Prepare early wheat stages from the supplied photograph on white.

Run from the repository root. Requires Pillow and numpy. The same seedling is
scaled proportionally for stages 0..4, following the vanilla growth heights;
stages 5..7 and the wheat item are not modified by this script.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE = Path('minecraft/wheat-reference/young.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 512
# Vanilla textures have approximately 3, 5, 7, 9 and 12 of 16 pixels of height.
HEIGHTS = (96, 160, 224, 288, 384)


def extract():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1024, 1024):
            raise ValueError('Expected the supplied 1024x1024 image')
        rgb = np.asarray(image, dtype=np.float32)
    # The background is near white, with low-level JPEG noise. Smoothly key
    # out white while preserving coloured leaves and antialiased boundaries.
    distance = 255.0 - rgb.min(axis=2)
    alpha = np.clip((distance - 5.0) / 28.0, 0.0, 1.0)
    color = np.clip((rgb - 255.0 * (1.0 - alpha[..., None])) /
                    np.maximum(alpha[..., None], 1.0 / 255.0), 0, 255)
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)))
    rgba[rgba[..., 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    bbox = plant.getchannel('A').point(lambda v: 255 if v >= 64 else 0).getbbox()
    if bbox is None:
        raise ValueError('No wheat seedling found')
    left, top, right, bottom = bbox
    return plant.crop((max(left-2, 0), max(top-2, 0), min(right+2, 1024), min(bottom+2, 1024)))


def prepare_stages():
    plant = extract()
    stages = []
    for height in HEIGHTS:
        width = max(1, round(plant.width * height / plant.height))
        scaled = plant.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(scaled, ((SIZE-width)//2, SIZE-height))
        stages.append(canvas)
    return stages


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i, image in enumerate(prepare_stages()):
        image.save(BLOCKS / f'wheat_stage_{i}.png', optimize=True)
    print('Prepared wheat stages 0..4 from the young wheat photograph.')


if __name__ == '__main__':
    main()
