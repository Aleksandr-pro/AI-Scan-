#!/usr/bin/env python3
"""Extract the supplied photo for the ordinary vanilla Bedrock bush block.

Run from the repository root. Requires Pillow and numpy. The black JPEG
background is keyed approximately; the bush item and other bushes are unchanged.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

SOURCE = Path('minecraft/bush-reference/bush.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/bush.png')
SIZE = 512
MAX_HEIGHT = 384  # vanilla bush texture occupies roughly 12/16 of a block


def prepare():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 843):
            raise ValueError('Expected the supplied 1264x843 JPG')
        rgb = np.asarray(image, dtype=np.float32)
    # Dark JPG background is not transparency; use a soft brightness key.
    alpha = np.clip((rgb.max(axis=2) - 5.0) / 24.0, 0.0, 1.0)
    color = np.clip(rgb / np.maximum(alpha[..., None], 1.0/255.0), 0, 255)
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    rgba[rgba[..., 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    bbox = plant.getchannel('A').point(lambda v: 255 if v >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError('No bush found')
    x0, y0, x1, y1 = bbox
    plant = plant.crop((max(0, x0-2), max(0, y0-2), min(plant.width, x1+2), min(plant.height, y1+2)))
    plant.thumbnail((SIZE-8, MAX_HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    bottom = plant.getchannel('A').getbbox()[3]
    canvas.paste(plant, ((SIZE-plant.width)//2, SIZE-bottom))
    return canvas


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared ordinary bush texture: {OUTPUT}')


if __name__ == '__main__':
    main()
