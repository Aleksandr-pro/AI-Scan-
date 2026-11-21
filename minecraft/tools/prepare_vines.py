#!/usr/bin/env python3
"""Prepare six ordinary-vine variations from the supplied black-background JPG.

Run from the repository root. Requires Pillow, numpy and scipy. The variants
are independent wall tiles, not a connected model: adjacent blocks may choose
unrelated images and do not form a guaranteed continuous vine.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label
from PIL import Image, ImageOps

SOURCE = Path('minecraft/vine-reference/vines.jpg')
BLOCKS = Path('minecraft/realistic-dirt/textures/blocks')
SIZE = 256
# Left curtain, slender strand, double curtain, small hanging vine, dense
# curtain, and the horizontal hanging branch, respectively.
CROPS = ((0, 0, 185, 655), (184, 0, 266, 655), (266, 0, 526, 655),
         (526, 220, 747, 655), (746, 220, 996, 655), (525, 0, 996, 224))


def prepare(variant):
    with Image.open(SOURCE) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        if image.size != (996, 665):
            raise ValueError('Expected the supplied 996x665 JPEG')
        rgb = np.asarray(image.crop(CROPS[variant]), dtype=np.float32)
    intensity = rgb.max(axis=2)
    alpha = np.clip((intensity-5)/24, 0, 1)
    # Suppress isolated low-level JPEG noise in the black backdrop, without
    # removing dark twig pixels adjacent to more visible leaves and branches.
    seed = intensity >= 32
    if not np.any(seed):
        raise ValueError(f'No vine in region {variant}')
    distance = distance_transform_edt(~seed)
    alpha = np.where((intensity < 32) & (distance > 4), 0, alpha)
    color = np.clip(rgb / np.maximum(alpha[..., None], 1/255), 0, 255)
    rgba = np.dstack((np.rint(color).astype(np.uint8), np.rint(alpha*255).astype(np.uint8)))
    # Remove isolated JPEG specks but retain separate leaves and strands.
    labels, count = label(alpha >= .38, structure=np.ones((3, 3), dtype=np.uint8))
    if count:
        sizes = np.bincount(labels.ravel())
        keep = sizes >= 12
        keep[0] = False
        rgba[~binary_dilation(keep[labels], structure=np.ones((3, 3)))] = 0
    rgba[rgba[:,:,3] == 0, :3] = 0
    plant = Image.fromarray(rgba)
    bounds = plant.getchannel('A').point(lambda a: 255 if a >= 96 else 0).getbbox()
    if not bounds:
        raise ValueError(f'Empty vine region {variant}')
    x0,y0,x1,y1 = bounds
    plant = plant.crop((max(0,x0-2), max(0,y0-2), min(plant.width,x1+2), min(plant.height,y1+2)))
    plant.thumbnail((SIZE-4, SIZE-4), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    # Hanging artwork starts at the upper edge, not at the soil plane.
    top = plant.getchannel('A').getbbox()[1]
    canvas.paste(plant, ((SIZE-plant.width)//2, -top))
    return canvas


def main():
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i in range(len(CROPS)):
        name = 'vine' if i == 0 else f'vine_variant_{i}'
        prepare(i).save(BLOCKS / f'{name}.png', optimize=True)
    print('Prepared six ordinary-vine variations.')


if __name__ == '__main__':
    main()
