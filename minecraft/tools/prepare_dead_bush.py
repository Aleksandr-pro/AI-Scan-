#!/usr/bin/env python3
"""Prepare the vanilla dead-bush texture from the supplied white-background JPG.

Run from the repository root. Requires Pillow, numpy and scipy. The brightness
matte is approximate and very thin branches may be altered by the JPEG or by
Minecraft's alpha testing. The live bush and game behaviour are not modified.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageOps

SOURCE = Path('minecraft/dead-bush-reference/dead-bush.jpg')
OUTPUT = Path('minecraft/realistic-dirt/textures/blocks/deadbush.png')
SIZE = 512


def prepare():
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (1264, 843):
            raise ValueError('Expected the supplied 1264x843 JPG')
        rgb = np.asarray(image, dtype=np.float32)
    # Fade the near-white background and JPEG noise while keeping soft edges.
    alpha = np.clip((255.0-rgb.min(axis=2)-5.0)/28.0, 0, 1)
    color = np.clip((rgb - 255.0*(1-alpha[..., None])) /
                    np.maximum(alpha[..., None], 1/255), 0, 255)
    # Recover darker local branch colour in pale background-contaminated edges.
    solid = (alpha > .98) & (rgb.min(axis=2) < 150)
    if not np.any(solid):
        raise ValueError('No dead bush found')
    nearest = distance_transform_edt(~solid, return_distances=False, return_indices=True)
    core_rgb = rgb[nearest[0], nearest[1]]
    weight = np.clip((rgb.min(axis=2)-150)/60, 0, 1)[..., None]
    color = color*(1-weight) + core_rgb*weight
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    rgba[rgba[:, :, 3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    bbox = plant.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if bbox is None:
        raise ValueError('Empty bush')
    x0, y0, x1, y1 = bbox
    plant = plant.crop((max(0, x0-2), max(0, y0-2), min(plant.width, x1+2), min(plant.height, y1+2)))
    plant.thumbnail((SIZE-8, SIZE-4), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    bottom = plant.getchannel('A').getbbox()[3]
    canvas.paste(plant, ((SIZE-plant.width)//2, SIZE-bottom))
    return canvas


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prepare().save(OUTPUT, optimize=True)
    print(f'Prepared dead bush texture: {OUTPUT}')


if __name__ == '__main__':
    main()
